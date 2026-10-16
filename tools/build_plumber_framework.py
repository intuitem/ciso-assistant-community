#!/usr/bin/env python3
"""Build the Plumber CI/CD checks framework library from the plumber source.

Parses control/codes.go (issue codes: title, description, remediation, severity,
control key) and configuration/registry.go (controlsMeta: display name, category,
CTRL id, description, providers, GitLab tier; plus the bench) of a
getplumber/plumber checkout and regenerates
backend/library/libraries/plumber-cicd-checks.yaml.

One requirement per CONTROL (ref_id = the camelCase .plumber.yaml control key),
not per issue code. Provider applicability and the bench are both keyed by
control upstream, so implementation-group membership is native at this
granularity. The ISSUE codes a control owns — with their individual severities,
titles, remediation and doc URLs — are carried in the node annotation, which is
also what a scan-result importer joins on.

Implementation groups are derived from what plumber ACTUALLY RUNS, not from
declared applicability: a control benched for a provider never has its rego
loaded (control/bench_filter.go) and its findings are dropped before scoring
(control/catalog.go). Controls benched on every provider land in `not-enforced`.

Usage:
    python tools/build_plumber_framework.py /path/to/plumber
    python tools/build_plumber_framework.py --clone

When the framework content differs from the existing library file, the library
`version` integer is incremented and `publication_date` set to today; otherwise
the file is left untouched. Removed/renamed control keys are reported loudly: a
changed ref_id means a new URN, i.e. loss of assessment continuity on update.
"""

import argparse
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import yaml

REPO_URL = "https://github.com/getplumber/plumber.git"
OUTPUT = (
    Path(__file__).resolve().parent.parent
    / "backend/library/libraries/plumber-cicd-checks.yaml"
)

LIB_URN = "urn:intuitem:risk:library:plumber-cicd-checks"
FW_URN = "urn:intuitem:risk:framework:plumber-cicd-checks"
NODE_BASE = "urn:intuitem:risk:req_node:plumber-cicd-checks"
DOCS_BASE = "https://getplumber.io/docs/cli/issues/"

IG_GITHUB, IG_GITLAB, IG_COMMON, IG_NOT_ENFORCED = (
    "github",
    "gitlab",
    "common",
    "not-enforced",
)

ENTRY_RE = re.compile(
    r"\{\s*"
    r"Code:\s+(\w+),\s*"
    r"Severity:\s+Severity(\w+),\s*"
    r'Title:\s+"((?:[^"\\]|\\.)*)",\s*'
    r'Description:\s+"((?:[^"\\]|\\.)*)",\s*'
    r'Remediation:\s+"((?:[^"\\]|\\.)*)",\s*'
    r"DocURL:\s+docsBaseURL \+ string\(\w+\),\s*"
    r'ControlName:\s+"(\w+)",',
    re.S,
)
CONST_RE = re.compile(r'(Code\w+)\s+ErrorCode = "(ISSUE-\d+)"')
BENCH_ENTRY_RE = re.compile(r'"(\w+)":\s*\{\}')
CATEGORY_RE = re.compile(r'^\t(Category\w+)\s*=\s*"([^"]*)"', re.M)
META_ENTRY_RE = re.compile(r'^\t"(\w+)": \{\n(.*?)^\t\},$', re.M | re.S)
META_FIELD_RE = re.compile(r"^\t\t(\w+):\s+(.*?),?$", re.M)
GO_STRING_RE = re.compile(r'^"((?:[^"\\]|\\.)*)"$')

TIER_LABELS = {"TierPremium": "GitLab Premium", "TierUltimate": "GitLab Ultimate"}


def unescape(s: str) -> str:
    return s.replace('\\"', '"').replace("\\\\", "\\")


def go_string(value: str, field: str, control: str) -> str:
    m = GO_STRING_RE.match(value)
    if not m:
        sys.exit(
            f"{control}.{field} is not a string literal (registry.go format drift?)"
        )
    return unescape(m.group(1))


def parse_controls_meta(registry_go: str):
    """controlsMeta -> {control: meta} and the category names in declaration order."""
    categories = dict(CATEGORY_RE.findall(registry_go))
    start = registry_go.index("var controlsMeta")
    end = registry_go.index("\n}\n", start)
    controls = {}
    for key, body in META_ENTRY_RE.findall(registry_go[start:end]):
        fields = dict(META_FIELD_RE.findall(body))
        missing = {"Providers", "DisplayName", "Category", "ID", "Description"} - set(
            fields
        )
        if missing:
            sys.exit(f"controlsMeta.{key} lacks {sorted(missing)} (format drift?)")
        if fields["Category"] not in categories:
            sys.exit(f"controlsMeta.{key}: unknown category {fields['Category']}")
        controls[key] = {
            "providers": {
                p.strip().replace("Provider", "").lower()
                for p in fields["Providers"].split("{", 1)[1].rstrip("}").split(",")
                if p.strip()
            },
            "name": go_string(fields["DisplayName"], "DisplayName", key),
            "category": categories[fields["Category"]],
            "id": go_string(fields["ID"], "ID", key),
            "description": go_string(fields["Description"], "Description", key),
            "requires_config": fields.get("RequiresConfig") == "true",
            "tier": TIER_LABELS.get(fields.get("Tier", "")),
        }
    if not controls:
        sys.exit("no controlsMeta entries parsed (registry.go format drift?)")
    return controls, list(categories.values())


def parse_plumber(repo: Path):
    codes_go = (repo / "control/codes.go").read_text()
    registry_go = (repo / "configuration/registry.go").read_text()

    const_to_code = dict(CONST_RE.findall(codes_go))
    entries = {}
    for m in ENTRY_RE.finditer(codes_go):
        const, sev, title, desc, rem, control = m.groups()
        code = const_to_code[const]
        entries[code] = {
            "code": code,
            "severity": sev.lower(),
            "title": unescape(title),
            "description": unescape(desc),
            "remediation": unescape(rem),
            "control": control,
        }
    missing = set(const_to_code.values()) - set(entries)
    if missing:
        sys.exit(f"unparsed issue codes (codes.go format drift?): {sorted(missing)}")

    controls, categories = parse_controls_meta(registry_go)
    unknown = {e["control"] for e in entries.values()} - set(controls)
    if unknown:
        sys.exit(
            f"issue codes owned by controls absent from controlsMeta: {sorted(unknown)}"
        )

    bench = parse_bench(registry_go, set(controls))

    version = commit = None
    m = re.search(r"##? \[(\d+\.\d+\.\d+)\]", (repo / "CHANGELOG.md").read_text())
    if m:
        version = m.group(1)
    rev = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if rev.returncode == 0:
        commit = rev.stdout.strip()
    return entries, controls, categories, bench, version, commit


def parse_bench(registry_go: str, known: set[str]) -> dict[str, set[str]]:
    """benchedControls: {provider: {control, ...}}. Empty provider blocks are valid."""
    start = registry_go.index("var benchedControls")
    end = registry_go.find("\n}\n", start)
    block = registry_go[start:end]
    bench: dict[str, set[str]] = {}
    marks = [(m.start(), m.group(1)) for m in re.finditer(r"Provider(\w+):", block)]
    for i, (pos, provider) in enumerate(marks):
        stop = marks[i + 1][0] if i + 1 < len(marks) else len(block)
        bench[provider.lower()] = set(BENCH_ENTRY_RE.findall(block[pos:stop]))
    stray = set().union(*bench.values()) - known if bench else set()
    if stray:
        sys.exit(f"benched controls absent from controlsMeta: {sorted(stray)}")
    return bench


def implementation_groups(control: str, providers: set[str], bench) -> list[str]:
    """What plumber actually runs for this control, per provider."""
    ships = {p for p in providers if control not in bench.get(p, set())}
    if not ships:
        return [IG_NOT_ENFORCED]
    groups = sorted(ships)
    if len(ships) > 1:
        groups.append(IG_COMMON)
    return groups


def build_nodes(entries, controls, categories, bench):
    by_control: dict[str, list[dict]] = {}
    for e in sorted(entries.values(), key=lambda e: int(e["code"].split("-")[1])):
        by_control.setdefault(e["control"], []).append(e)

    nodes = []
    for index, category in enumerate(categories, start=1):
        members = sorted(
            (c for c, meta in controls.items() if meta["category"] == category),
            key=lambda c: controls[c]["id"],
        )
        if not members:
            continue
        cat_urn = f"{NODE_BASE}:{index}"
        nodes.append(
            {
                "urn": cat_urn,
                "assessable": False,
                "depth": 1,
                "ref_id": str(index),
                "name": category,
            }
        )
        for control in members:
            meta = controls[control]
            codes = by_control.get(control, [])
            lines = [f"Plumber control: {meta['id']}."]
            if meta["requires_config"]:
                lines.append(
                    "Needs settings in .plumber.yaml before it can be evaluated."
                )
            if meta["tier"]:
                lines.append(f"Requires {meta['tier']} or higher.")
            lines += [
                f"- {c['code']} ({c['severity']}) {c['title']}\n"
                f"  {c['remediation']}\n"
                f"  {DOCS_BASE}{c['code']}"
                for c in codes
            ]
            nodes.append(
                {
                    "urn": f"{NODE_BASE}:{control.lower()}",
                    "assessable": True,
                    "depth": 2,
                    "parent_urn": cat_urn,
                    "ref_id": control,
                    "name": meta["name"],
                    "description": meta["description"],
                    "annotation": "\n".join(lines),
                    "implementation_groups": implementation_groups(
                        control, meta["providers"], bench
                    ),
                }
            )
    return nodes


def build_library(nodes, plumber_version, commit, lib_version, publication_date):
    pin = ""
    if plumber_version:
        pin = f" Based on plumber v{plumber_version}"
        pin += f" (commit {commit})." if commit else "."
    return {
        "urn": LIB_URN,
        "locale": "en",
        "ref_id": "plumber-cicd-checks",
        "name": "Plumber CI/CD Security Checks",
        "description": (
            "CI/CD pipeline security checks performed by Plumber, the open-source"
            " CI/CD security scanner for GitLab CI and GitHub Actions"
            " (getplumber.io).\nEach requirement corresponds to a Plumber control"
            f" (the .plumber.yaml key).{pin}"
            "\nhttps://github.com/getplumber/plumber"
        ),
        "copyright": "Plumber contributors - Mozilla Public License 2.0",
        "version": lib_version,
        "publication_date": publication_date,
        "provider": "Plumber",
        "packager": "intuitem",
        "objects": {
            "framework": {
                "urn": FW_URN,
                "ref_id": "plumber-cicd-checks",
                "name": "Plumber CI/CD Security Checks",
                "description": (
                    "CI/CD pipeline security checks performed by Plumber, the"
                    " open-source CI/CD security scanner for GitLab CI and GitHub"
                    " Actions. Each assessable requirement is a Plumber control —"
                    " the ref_id is the .plumber.yaml key that enables it, grouped"
                    " by Plumber's own control categories. The annotation gives"
                    " the Plumber control ID and lists the ISSUE codes the control"
                    " emits, with their severity, remediation and documentation"
                    " URL."
                    "\nImplementation groups reflect what Plumber actually runs:"
                    " controls whose rules are implemented but not yet enforced"
                    " upstream (pending test coverage) are grouped under"
                    " 'not-enforced' and can only be assessed manually."
                ),
                "implementation_groups_definition": [
                    {
                        "ref_id": IG_GITHUB,
                        "name": "GitHub Actions",
                        "description": "Controls Plumber enforces when scanning"
                        " GitHub Actions workflows and repository settings.",
                    },
                    {
                        "ref_id": IG_GITLAB,
                        "name": "GitLab CI",
                        "description": "Controls Plumber enforces when scanning"
                        " GitLab CI pipelines and project settings.",
                    },
                    {
                        "ref_id": IG_COMMON,
                        "name": "Cross-provider",
                        "description": "Controls Plumber enforces on both GitHub"
                        " and GitLab — the provider-agnostic core.",
                    },
                    {
                        "ref_id": IG_NOT_ENFORCED,
                        "name": "Not yet enforced",
                        "description": "Controls implemented in Plumber but held"
                        " back from enforcement pending test coverage. No scan"
                        " reports on them; assess them manually or exclude them.",
                    },
                ],
                "requirement_nodes": nodes,
            }
        },
    }


class Dumper(yaml.SafeDumper):
    pass


def str_presenter(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


Dumper.add_representer(str, str_presenter)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plumber", nargs="?", help="path to a plumber checkout")
    parser.add_argument(
        "--clone", action="store_true", help=f"shallow-clone {REPO_URL} instead"
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--min-version",
        type=int,
        default=1,
        help="floor for the library version. The file on disk cannot know what has"
        " already been stored or loaded elsewhere; pass the highest version that"
        " exists anywhere so a rebuild never collides with it (a same-urn,"
        " same-version import is silently discarded by StoredLibrary).",
    )
    args = parser.parse_args()
    if bool(args.plumber) == args.clone:
        parser.error("pass a plumber checkout path OR --clone")

    if args.clone:
        tmp = tempfile.mkdtemp(prefix="plumber-")
        subprocess.run(["git", "clone", "--depth", "1", REPO_URL, tmp], check=True)
        repo = Path(tmp)
    else:
        repo = Path(args.plumber)

    entries, controls, categories, bench, plumber_version, commit = parse_plumber(repo)
    nodes = build_nodes(entries, controls, categories, bench)

    existing = None
    if args.output.exists():
        existing = yaml.safe_load(args.output.read_text())

    lib_version = max(1, args.min_version)
    publication_date = date.today()
    if existing:
        candidate = yaml.safe_load(
            yaml.dump(
                build_library(nodes, None, None, 0, None)["objects"], Dumper=Dumper
            )
        )
        unchanged = existing["objects"] == candidate
        current = int(existing["version"])
        if unchanged and current >= args.min_version:
            print(f"no framework change — keeping version {current}")
            return
        lib_version = max(current + (0 if unchanged else 1), args.min_version)
        old = {
            n["ref_id"]
            for n in existing["objects"]["framework"]["requirement_nodes"]
            if n.get("assessable")
        }
        new = {n["ref_id"] for n in nodes if n["assessable"]}
        if added := sorted(new - old):
            print(f"added: {', '.join(added)}")
        if removed := sorted(old - new):
            print(
                f"WARNING — removed/renamed controls (URN change breaks assessment"
                f" continuity, check plumber changelog): {', '.join(removed)}"
            )

    library = build_library(
        nodes, plumber_version, commit, lib_version, publication_date
    )
    args.output.write_text(
        yaml.dump(library, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=88)
    )

    tally = {}
    for n in nodes:
        if n["assessable"]:
            for g in n["implementation_groups"]:
                tally[g] = tally.get(g, 0) + 1
    assessable = sum(1 for n in nodes if n["assessable"])
    print(
        f"wrote {args.output} — version {lib_version}, plumber v{plumber_version}"
        f" ({commit}), {assessable} controls / {len(entries)} issue codes"
    )
    print("   " + ", ".join(f"{g}: {c}" for g, c in sorted(tally.items())))


if __name__ == "__main__":
    main()
