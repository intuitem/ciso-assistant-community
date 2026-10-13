#!/usr/bin/env python3
"""Build the Plumber CI/CD checks framework library from the plumber source.

Parses control/codes.go (issue codes: title, description, remediation, severity,
control key) and configuration/registry.go (provider applicability + the bench)
of a getplumber/plumber checkout and regenerates
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

# Categories mirror plumber's documented taxonomy (docs/GITHUB_ISSUES.md TOC
# sections, also used by the init wizard and the getplumber.io issue pages).
# Codes are listed here because that is the level plumber documents; each
# control inherits the category of its codes and the build fails if a control's
# codes disagree. A new issue code lands in exactly one list.
CATEGORIES = [
    (
        "1",
        "Supply chain",
        "Integrity and provenance of the third-party building blocks a pipeline"
        " executes: container images, GitHub Actions references, ambiguous"
        " tag/branch refs, Dockerfile base images, build caches and released"
        " artefacts.",
        [
            101,
            102,
            103,
            402,
            701,
            702,
            703,
            704,
            705,
            706,
            707,
            708,
            709,
            711,
            712,
            713,
            714,
            715,
            716,
        ],
    ),
    (
        "2",
        "Expressions and injections",
        "Safe handling of CI/CD variables and template expressions: debug traces,"
        " unsafe expansion, template injection of user- or maintainer-controlled"
        " values into shell scripts, and deprecated workflow commands.",
        [203, 204, 205, 207, 208, 209, 210, 211, 212, 213, 214, 215],
    ),
    (
        "3",
        "Secrets, credentials and permissions",
        "Protection of secrets and tokens consumed by pipelines: hardcoded leaks,"
        " over-broad forwarding, redaction bypasses, token lifetime, environment"
        " gating and explicit workflow permissions.",
        [302, 303, 305, 306, 307, 308, 309, 801],
    ),
    (
        "4",
        "Triggers and composition",
        "Governance of what a pipeline is made of and what it executes: required"
        " templates and components, hardcoded jobs, weakened security jobs,"
        " unverified script execution, Docker-in-Docker and dangerous triggers.",
        [401, 403, 404, 405, 406, 408, 409, 410, 411, 412, 413, 417, 802, 804],
    ),
    (
        "5",
        "Access and authorisation",
        "Platform-side guardrails on who can change what: branch protection and"
        " overly broad workflow permission grants.",
        [501, 505, 803],
    ),
    (
        "6",
        "Workflow hygiene",
        "Repository-level and workflow-level hygiene: concurrency, naming,"
        " obfuscation, trusted publishing, dependency update tooling, SAST"
        " coverage and security policy.",
        [418, 419, 420, 421, 601, 901, 902, 903, 904, 905],
    ),
]

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
META_RE = re.compile(r'"(\w+)":\s+\{Providers: \[\]string\{([^}]*)\}\}')
BENCH_ENTRY_RE = re.compile(r'"(\w+)":\s*\{\}')
WORD_SPLIT_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

# A camelCase key cannot encode the casing of proper nouns, acronyms or
# identifiers, so splitting it yields "Git Hub", "Sha", "CV Es". Deriving the
# casing from plumber's own prose was tried and rejected: its descriptions use
# emphatic capitals ("a MOVING ref"), Dockerfile FROM and $GITHUB_ENV, which
# poison any corpus-built dictionary. Keys are matched on letters only, so one
# entry covers both "Git"+"Hub" and a leading lowercase "github".
TERMS = {
    "github": "GitHub",
    "sha": "SHA",
    "oidc": "OIDC",
    "fromjson": "fromJSON",
    "cves": "CVEs",
    "reenable": "Re-Enable",
}


def unescape(s: str) -> str:
    return s.replace('\\"', '"').replace("\\\\", "\\")


def humanize(control: str) -> str:
    """camelCase control key -> requirement statement, restoring known casings."""
    words = WORD_SPLIT_RE.split(control)
    out: list[str] = []
    i = 0
    while i < len(words):
        for j in range(min(len(words), i + 2), i - 1, -1):
            joined = re.sub(r"[^a-z]", "", "".join(words[i : j + 1]).lower())
            if term := TERMS.get(joined):
                out.append(term)
                i = j + 1
                break
        else:
            out.append(words[i][:1].upper() + words[i][1:])
            i += 1
    name = " ".join(out)
    return name[:1].upper() + name[1:]


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

    providers = {
        ctl: {p.strip().replace("Provider", "").lower() for p in provs.split(",")}
        for ctl, provs in META_RE.findall(registry_go)
    }
    unknown = {e["control"] for e in entries.values()} - set(providers)
    if unknown:
        sys.exit(
            f"controls missing from registry.go (format drift?): {sorted(unknown)}"
        )

    bench = parse_bench(registry_go, set(providers))

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
    return entries, providers, bench, version, commit


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


def implementation_groups(control: str, providers, bench) -> list[str]:
    """What plumber actually runs for this control, per provider."""
    ships = {p for p in providers[control] if control not in bench.get(p, set())}
    if not ships:
        return [IG_NOT_ENFORCED]
    groups = sorted(ships)
    if len(ships) > 1:
        groups.append(IG_COMMON)
    return groups


def build_nodes(entries, providers, bench):
    covered = [n for _, _, _, nums in CATEGORIES for n in nums]
    if len(covered) != len(set(covered)):
        sys.exit("duplicate issue code in CATEGORIES")
    parsed = {int(c.split("-")[1]) for c in entries}
    if set(covered) != parsed:
        sys.exit(
            f"CATEGORIES out of sync with codes.go — "
            f"new codes to place: {sorted(parsed - set(covered))}, "
            f"gone from codes.go: {sorted(set(covered) - parsed)}"
        )

    cat_of_code = {num: ref for ref, _, _, nums in CATEGORIES for num in nums}
    by_control: dict[str, list[dict]] = {}
    for e in sorted(entries.values(), key=lambda e: int(e["code"].split("-")[1])):
        by_control.setdefault(e["control"], []).append(e)

    cat_of_control = {}
    for control, codes in by_control.items():
        cats = {cat_of_code[int(c["code"].split("-")[1])] for c in codes}
        if len(cats) > 1:
            sys.exit(
                f"control {control} spans categories {sorted(cats)} — "
                f"codes {[c['code'] for c in codes]}; fix CATEGORIES"
            )
        cat_of_control[control] = cats.pop()

    nodes = []
    for cat_ref, cat_name, cat_desc, _ in CATEGORIES:
        nodes.append(
            {
                "urn": f"{NODE_BASE}:{cat_ref}",
                "assessable": False,
                "depth": 1,
                "ref_id": cat_ref,
                "name": cat_name,
                "description": cat_desc,
            }
        )
        members = sorted(c for c, r in cat_of_control.items() if r == cat_ref)
        for control in members:
            codes = by_control[control]
            severities = " / ".join(f"{c['code']} {c['severity']}" for c in codes)
            detail = "\n".join(
                f"- {c['code']} ({c['severity']}) {c['title']}\n"
                f"  {c['remediation']}\n"
                f"  {DOCS_BASE}{c['code']}"
                for c in codes
            )
            nodes.append(
                {
                    "urn": f"{NODE_BASE}:{control.lower()}",
                    "assessable": True,
                    "depth": 2,
                    "parent_urn": f"{NODE_BASE}:{cat_ref}",
                    "ref_id": control,
                    "name": humanize(control),
                    "description": "\n".join(c["description"] for c in codes),
                    "annotation": f"Severity: {severities}.\n{detail}",
                    "implementation_groups": implementation_groups(
                        control, providers, bench
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
                    " the ref_id is the .plumber.yaml key that enables it. The"
                    " annotation lists the ISSUE codes the control emits, with"
                    " their severity, remediation and documentation URL."
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

    entries, providers, bench, plumber_version, commit = parse_plumber(repo)
    nodes = build_nodes(entries, providers, bench)

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
