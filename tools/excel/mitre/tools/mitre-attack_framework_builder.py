#!/usr/bin/env python3
"""Build a CISO Assistant MITRE ATT&CK Excel library for one ATT&CK domain.

Handles the Enterprise, ICS and Mobile matrices. Each one is emitted as a TTP
library: a `ttp_catalog` block, `tactics` in matrix column order, `techniques`
carrying their parent, tactics, facet groups and mitigations, and the
mitigations themselves as reference controls.

The complete pipeline is handled by this script:

1. Download README.md, LICENSE.txt and the domain STIX bundle from mitre/cti.
2. Read the ATT&CK version from the bundle's latest release commit.
3. Carry forward the French translations of the shipped library, when present.
4. Build the final, versioned CISO Assistant workbook.
5. Delete downloaded files unless `-k/--keep` is used.

Run from shell:

    python ./mitre-attack_framework_builder.py --domain enterprise
    python ./mitre-attack_framework_builder.py --domain ics --keep
    python ./mitre-attack_framework_builder.py --domain all

Then convert the workbook with `tools/convert_library_v2.py`.

Translations are carried forward per URN from the library already shipped in
`backend/library/libraries/`, so regenerating a translated domain never drops
its existing French. Cells with nothing to carry stay empty unless
`--translation-formulas` is passed, which fills them with `=TRADUIRE(...)`.

ATT&CK publishes a handful of mitigations verbatim in several domains (Mobile
M1013 is Enterprise M1013). Re-declaring one breaks the (ref_id, name)
uniqueness ReferenceControl enforces per folder, so the Enterprise library is
read at build time and a repeat is referenced through a library dependency
instead of being emitted again.

Manual steps for those formulas in the final workbook:

- To activate the French translation formulas, manually remove the `@` in
  front of the `=`. Excel's Find and Replace tool can help, but process about
  100 cells at a time instead of replacing every cell at once to avoid hitting
  the translation API limit too quickly.
- After the formulas finish translating, copy the translated cells and paste
  them back into the same location using Paste Values. This ensures that the
  exported YAML contains the actual translations; otherwise, it may contain
  unexpected formula-related text instead.
- Some source text may be too long for the translation function. Translate
  those cells manually (e.g. with DeepL).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urlparse

import requests
import yaml
from mitreattack.stix20 import MitreAttackData
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.worksheet import Worksheet

try:
    from tqdm import tqdm
except ModuleNotFoundError:  # pragma: no cover
    tqdm = None


# ---------------------------------------------------------------------------
# Fixed configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]
LIBRARIES_DIR = REPO_ROOT / "backend" / "library" / "libraries"

RAW_BASE_URL = "https://raw.githubusercontent.com/mitre/cti/master"
README_URL = f"{RAW_BASE_URL}/README.md"
LICENSE_URL = f"{RAW_BASE_URL}/LICENSE.txt"
COMMITS_API_URL = "https://api.github.com/repos/mitre/cti/commits"
SOURCE_URL = "https://github.com/mitre/cti"

README_PATH = SCRIPT_DIR / "README.md"
LICENSE_PATH = SCRIPT_DIR / "LICENSE.txt"

LIBRARY_VERSION = "1"
LIBRARY_LOCALE = "en"
LIBRARY_PROVIDER = "Mitre ATT&CK"
LIBRARY_PACKAGER = "intuitem"

LIBRARY_META_SHEET = "library_meta"
CATALOG_META_SHEET = "ttp_catalog_meta"
CATALOG_CONTENT_SHEET = "ttp_catalog_content"
GROUPS_META_SHEET = "ttp_groups_meta"
GROUPS_CONTENT_SHEET = "ttp_groups_content"
TACTICS_META_SHEET = "tactics_meta"
TACTICS_CONTENT_SHEET = "tactics_content"
TECHNIQUES_META_SHEET = "techniques_meta"
TECHNIQUES_CONTENT_SHEET = "techniques_content"
MITIGATIONS_META_SHEET = "mitigations_meta"
MITIGATIONS_CONTENT_SHEET = "mitigations_content"

GROUPING_BLOCK_NAME = "ttp_groups"

# The source STIX objects do not provide a NIST CSF function. Enterprise values
# are preserved from the pre-TTP mitre-attack.xlsx library. A future mitigation
# which is not in this mapping is assigned to "protect" and reported.
ENTERPRISE_CSF_FUNCTIONS = {
    "M1013": "govern",
    "M1015": "protect",
    "M1016": "detect",
    "M1017": "govern",
    "M1018": "protect",
    "M1019": "protect",
    "M1020": "protect",
    "M1021": "protect",
    "M1022": "protect",
    "M1024": "protect",
    "M1025": "protect",
    "M1026": "protect",
    "M1027": "protect",
    "M1028": "protect",
    "M1029": "protect",
    "M1030": "protect",
    "M1031": "detect",
    "M1032": "protect",
    "M1033": "protect",
    "M1034": "protect",
    "M1035": "protect",
    "M1036": "protect",
    "M1037": "protect",
    "M1038": "protect",
    "M1039": "protect",
    "M1040": "detect",
    "M1041": "protect",
    "M1042": "protect",
    "M1043": "protect",
    "M1044": "protect",
    "M1045": "protect",
    "M1046": "protect",
    "M1047": "protect",
    "M1048": "protect",
    "M1049": "detect",
    "M1050": "detect",
    "M1051": "protect",
    "M1052": "protect",
    "M1053": "recover",
    "M1054": "protect",
    "M1055": "govern",
    "M1056": "govern",
    "M1057": "detect",
    "M1060": "protect",
}

# ICS reuses 33 Enterprise mitigations under its own numbering: M09NN is the
# twin of Enterprise M10NN, so only the 19 OT-native ones are curated here.
ICS_NATIVE_CSF_FUNCTIONS = {
    "M0800": "protect",
    "M0801": "protect",
    "M0802": "protect",
    "M0803": "detect",
    "M0804": "protect",
    "M0805": "protect",
    "M0806": "protect",
    "M0807": "protect",
    "M0808": "protect",
    "M0809": "protect",
    "M0810": "recover",
    "M0811": "recover",
    "M0812": "protect",
    "M0813": "protect",
    "M0814": "protect",
    "M0815": "detect",
    "M0817": "govern",
    "M0818": "protect",
}

MOBILE_CSF_FUNCTIONS = {
    "M1001": "protect",
    "M1002": "detect",
    "M1003": "protect",
    "M1004": "protect",
    "M1006": "protect",
    "M1009": "protect",
    "M1010": "detect",
    "M1011": "govern",
    "M1012": "govern",
    "M1013": "govern",
    "M1014": "protect",
    "M1058": "detect",
}

# Placeholders standing in for "there is nothing to implement here". They are
# not controls, so they never become reference controls.
NON_MITIGATIONS = {
    "M0816",  # ICS - Mitigation Limited or Not Effective
    "M1059",  # Mobile - Do Not Mitigate
}


def _ics_csf_functions() -> dict[str, str]:
    functions = dict(ICS_NATIVE_CSF_FUNCTIONS)
    for ref_id, value in ENTERPRISE_CSF_FUNCTIONS.items():
        functions[f"M09{ref_id[3:]}"] = value
    return functions


@dataclass(frozen=True)
class DomainSpec:
    key: str
    bundle_name: str
    commit_label: str
    ref_id: str
    title: str
    catalog_name: str
    catalog_description: str
    grouping_dimension: str
    csf_functions: dict[str, str] = field(default_factory=dict)
    # ATT&CK repeats a few mitigations verbatim across domains; re-declaring one
    # breaks the (ref_id, name) uniqueness ReferenceControl enforces per folder.
    shared_library_ref_id: str | None = None

    @property
    def bundle_path(self) -> str:
        return f"{self.bundle_name}/{self.bundle_name}.json"

    @property
    def bundle_url(self) -> str:
        return f"{RAW_BASE_URL}/{self.bundle_path}"

    @property
    def local_bundle(self) -> Path:
        return SCRIPT_DIR / f"{self.bundle_name}.json"

    @property
    def library_urn(self) -> str:
        return f"urn:intuitem:risk:library:{self.ref_id}"

    @property
    def catalog_urn(self) -> str:
        return f"urn:intuitem:risk:ttp_catalog:{self.ref_id}"

    @property
    def tactics_base_urn(self) -> str:
        return f"urn:intuitem:risk:tactic:{self.ref_id}"

    @property
    def techniques_base_urn(self) -> str:
        return f"urn:intuitem:risk:technique:{self.ref_id}"

    @property
    def mitigations_base_urn(self) -> str:
        return f"urn:intuitem:risk:function:{self.ref_id}"

    @property
    def shipped_library(self) -> Path:
        return LIBRARIES_DIR / f"{self.ref_id}.yaml"


DOMAINS = {
    "enterprise": DomainSpec(
        key="enterprise",
        bundle_name="enterprise-attack",
        commit_label="Enterprise",
        ref_id="mitre-attack",
        title="Mitre ATT&CK",
        catalog_name="MITRE ATT&CK Enterprise Matrix",
        catalog_description=(
            "Tactics and techniques of the MITRE ATT&CK Enterprise matrix.\n"
            "https://attack.mitre.org"
        ),
        grouping_dimension="platform",
        csf_functions=ENTERPRISE_CSF_FUNCTIONS,
    ),
    "ics": DomainSpec(
        key="ics",
        bundle_name="ics-attack",
        commit_label="ICS",
        ref_id="mitre-attack-ics",
        title="Mitre ATT&CK for ICS",
        catalog_name="MITRE ATT&CK for ICS Matrix",
        catalog_description=(
            "Tactics and techniques of the MITRE ATT&CK for ICS matrix, covering "
            "adversary behaviour against industrial control systems.\n"
            "https://attack.mitre.org/matrices/ics"
        ),
        # x_mitre_platforms is empty for 82 of 97 ICS techniques; the targeted
        # asset is the dimension that actually carries information here.
        grouping_dimension="asset",
        csf_functions=_ics_csf_functions(),
        shared_library_ref_id="mitre-attack",
    ),
    "mobile": DomainSpec(
        key="mobile",
        bundle_name="mobile-attack",
        commit_label="Mobile",
        ref_id="mitre-attack-mobile",
        title="Mitre ATT&CK for Mobile",
        catalog_name="MITRE ATT&CK for Mobile Matrix",
        catalog_description=(
            "Tactics and techniques of the MITRE ATT&CK for Mobile matrix, covering "
            "adversary behaviour against Android and iOS devices.\n"
            "https://attack.mitre.org/matrices/mobile"
        ),
        grouping_dimension="platform",
        csf_functions=MOBILE_CSF_FUNCTIONS,
        shared_library_ref_id="mitre-attack",
    ),
}


@dataclass(frozen=True)
class Grouping:
    ref_id: str
    name: str


@dataclass(frozen=True)
class AttackRecord:
    ref_id: str
    name: str
    description: str


@dataclass(frozen=True)
class TechniqueRecord:
    ref_id: str
    name: str
    description: str
    parent_ref_id: str | None
    tactic_ref_ids: tuple[str, ...]
    groups: tuple[str, ...]
    mitigation_ref_ids: tuple[str, ...]


@dataclass(frozen=True)
class DomainContent:
    tactics: tuple[AttackRecord, ...]
    techniques: tuple[TechniqueRecord, ...]
    mitigations: tuple[AttackRecord, ...]
    groupings: tuple[Grouping, ...]
    # ref_id -> URN of the identical mitigation owned by another library
    aliased_mitigations: dict[str, str] = field(default_factory=dict)
    dependencies: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Display and download helpers
# ---------------------------------------------------------------------------


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(SCRIPT_DIR))
    except ValueError:
        return str(path)


def print_step_banner(step_number: int, title: str) -> None:
    message = f"##### [STEP {step_number}] {title} #####"
    line = "#" * len(message)
    print(f"\n{line}\n{message}\n{line}\n")


def validate_download_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")
    if parsed.hostname not in {"raw.githubusercontent.com", "api.github.com"}:
        raise ValueError(f"Unexpected download host: {parsed.hostname!r}")


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "Accept-Encoding": "identity",
            "User-Agent": "ciso-assistant-mitre-attack-framework-builder",
        }
    )
    return session


def download_file(
    session: requests.Session,
    url: str,
    destination: Path,
) -> None:
    validate_download_url(url)
    temporary_path = destination.with_name(f"{destination.name}.part")
    temporary_path.unlink(missing_ok=True)

    print(f'📥 [DOWN] Downloading: "{url}"')
    try:
        with session.get(url, stream=True, timeout=60) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("Content-Length", 0))
            with temporary_path.open("wb") as output:
                chunks = response.iter_content(chunk_size=64 * 1024)
                if tqdm is None:
                    for chunk in chunks:
                        if chunk:
                            output.write(chunk)
                else:
                    with tqdm(
                        total=total_size if total_size > 0 else None,
                        unit="o",
                        unit_scale=True,
                        unit_divisor=1024,
                        desc=destination.name,
                    ) as progress:
                        for chunk in chunks:
                            if not chunk:
                                continue
                            output.write(chunk)
                            progress.update(len(chunk))
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)

    print(f'✅ [OK] Downloaded: "{display_path(destination)}"')


def download_shared_sources(session: requests.Session) -> list[Path]:
    downloaded: list[Path] = []
    try:
        for url, destination in (
            (README_URL, README_PATH),
            (LICENSE_URL, LICENSE_PATH),
        ):
            download_file(session, url, destination)
            downloaded.append(destination)
    except Exception:
        cleanup(downloaded)
        raise
    return downloaded


def get_attack_version(session: requests.Session, domain: DomainSpec) -> str:
    validate_download_url(COMMITS_API_URL)
    response = session.get(
        COMMITS_API_URL,
        params={
            "path": domain.bundle_path,
            "sha": "master",
            "per_page": 100,
        },
        timeout=60,
    )
    response.raise_for_status()

    commits = response.json()
    if not isinstance(commits, list):
        raise ValueError("Unexpected response from the GitHub commits API")

    # the same path also receives commits labelled for another domain
    pattern = re.compile(
        rf"ATT&CK\s+v(?P<version>\d+(?:\.\d+)*)\s+{re.escape(domain.commit_label)}\b",
        flags=re.IGNORECASE,
    )
    for item in commits:
        message = item.get("commit", {}).get("message", "")
        match = pattern.search(message)
        if match:
            return match.group("version")

    raise ValueError(
        f"Unable to find an 'ATT&CK v# {domain.commit_label}' commit for "
        f"{domain.bundle_path}"
    )


# ---------------------------------------------------------------------------
# Source metadata extraction
# ---------------------------------------------------------------------------


def extract_markdown_section(markdown: str, heading: str) -> str:
    lines = markdown.splitlines()
    expected_heading = f"## {heading}"

    try:
        start = next(
            index
            for index, line in enumerate(lines)
            if line.strip() == expected_heading
        )
    except StopIteration as exc:
        raise ValueError(
            f"Section {expected_heading!r} not found in README.md"
        ) from exc

    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if lines[index].startswith("## ")
        ),
        len(lines),
    )
    section = "\n".join(lines[start + 1 : end]).strip()
    if not section:
        raise ValueError(f"Section {expected_heading!r} is empty in README.md")
    return section


def build_library_description(readme: str) -> str:
    attack_section = extract_markdown_section(readme, "ATT&CK")
    attack_section = re.sub(r"<(https?://[^>]+)>", r"\1", attack_section)
    return f"{attack_section}\n\nSource: {SOURCE_URL}"


def extract_attack_license(license_text: str) -> str:
    lines = license_text.splitlines()

    try:
        start = next(
            index for index, line in enumerate(lines) if line.strip() == "ATT&CK®"
        )
        end = next(
            index
            for index in range(start + 1, len(lines))
            if lines[index].strip() == "CAPEC™"
        )
    except StopIteration as exc:
        raise ValueError("ATT&CK license section not found in LICENSE.txt") from exc

    section = lines[start + 1 : end]
    while section and (not section[0].strip() or set(section[0].strip()) == {"="}):
        section.pop(0)
    while section and not section[-1].strip():
        section.pop()

    formatted: list[str] = []
    index = 0
    while index < len(section):
        line = section[index]
        stripped = line.strip()
        next_is_underline = (
            index + 1 < len(section)
            and bool(section[index + 1].strip())
            and set(section[index + 1].strip()) == {"-"}
        )

        if stripped in {"License", "Disclaimers"} and next_is_underline:
            if formatted and formatted[-1] != "":
                formatted.append("")
            formatted.extend((f"## {stripped}", ""))
            index += 2
            continue

        formatted.append(line.rstrip())
        index += 1

    copyright_text = "\n".join(formatted).strip()
    if not copyright_text.startswith("## License\n\n"):
        raise ValueError("The ATT&CK License heading could not be formatted")
    if "\n## Disclaimers\n\n" not in copyright_text:
        raise ValueError("The ATT&CK Disclaimers heading could not be formatted")
    return copyright_text


# ---------------------------------------------------------------------------
# ATT&CK extraction
# ---------------------------------------------------------------------------


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def get_external_reference(stix_object: object) -> tuple[str, str]:
    references = getattr(stix_object, "external_references", ())
    for reference in references:
        source_name = getattr(reference, "source_name", None)
        if source_name not in {
            "mitre-attack",
            "mitre-ics-attack",
            "mitre-mobile-attack",
        }:
            continue
        ref_id = getattr(reference, "external_id", None)
        url = getattr(reference, "url", None)
        if ref_id and url:
            return str(ref_id), str(url)

    raise ValueError(
        f"No complete ATT&CK external reference for "
        f"{getattr(stix_object, 'id', '<unknown>')}"
    )


def to_attack_record(stix_object: object) -> AttackRecord:
    ref_id, url = get_external_reference(stix_object)
    name = str(getattr(stix_object, "name")).strip()
    description = str(getattr(stix_object, "description", "")).strip()
    if not description:
        description = url
    elif url not in description:
        description = f"{description}\n{url}"
    return AttackRecord(ref_id=ref_id, name=name, description=description)


def is_active(stix_object: object) -> bool:
    return not getattr(stix_object, "revoked", False) and not getattr(
        stix_object, "x_mitre_deprecated", False
    )


def get_matrix_tactics(attack_data: MitreAttackData) -> list[object]:
    """Tactics in matrix column order. A domain can carry a deprecated matrix."""
    matrices = [
        matrix
        for matrix in attack_data.get_objects_by_type("x-mitre-matrix")
        if is_active(matrix)
    ]
    if len(matrices) != 1:
        names = ", ".join(str(getattr(m, "name", "?")) for m in matrices) or "none"
        raise ValueError(f"Expected exactly one active matrix, found: {names}")

    tactics = []
    for stix_id in matrices[0].tactic_refs:
        tactic = attack_data.get_object_by_stix_id(stix_id)
        if tactic is not None and is_active(tactic):
            tactics.append(tactic)
    return tactics


def _stix_id_to_ref_id(attack_data: MitreAttackData, stix_id: str) -> str | None:
    stix_object = attack_data.get_object_by_stix_id(stix_id)
    if stix_object is None:
        return None
    try:
        return get_external_reference(stix_object)[0]
    except ValueError:
        return None


def load_shared_mitigations(
    domain: DomainSpec,
) -> tuple[dict[str, tuple[str, str]], str]:
    """Reference controls of the library this domain may share mitigations with.

    Returns {ref_id: (name, urn)} and the library URN, or ({}, "") when there is
    no shared library or it is not on disk yet.
    """
    if not domain.shared_library_ref_id:
        return {}, ""

    path = LIBRARIES_DIR / f"{domain.shared_library_ref_id}.yaml"
    if not path.exists():
        print(
            f'⚠️  [WARNING] "{display_path(path)}" not found; mitigations repeated '
            "across ATT&CK domains cannot be detected.",
            file=sys.stderr,
        )
        return {}, ""

    with path.open(encoding="utf-8") as stream:
        library = yaml.safe_load(stream) or {}

    controls = {}
    for entry in (library.get("objects") or {}).get("reference_controls") or []:
        ref_id = entry.get("ref_id")
        if ref_id and entry.get("urn"):
            controls[str(ref_id).strip()] = (
                str(entry.get("name") or "").strip(),
                entry["urn"],
            )
    return controls, library.get("urn", "")


def extract_domain_content(source: Path, domain: DomainSpec) -> DomainContent:
    attack_data = MitreAttackData(str(source))

    tactic_objects = get_matrix_tactics(attack_data)
    tactics = tuple(to_attack_record(item) for item in tactic_objects)
    shortname_to_ref_id = {
        getattr(item, "x_mitre_shortname"): record.ref_id
        for item, record in zip(tactic_objects, tactics)
    }

    all_mitigations = sorted(
        (
            to_attack_record(item)
            for item in attack_data.get_mitigations(remove_revoked_deprecated=True)
            if get_external_reference(item)[0] not in NON_MITIGATIONS
        ),
        key=lambda item: item.ref_id,
    )

    shared, shared_library_urn = load_shared_mitigations(domain)
    aliased_mitigations = {
        item.ref_id: shared[item.ref_id][1]
        for item in all_mitigations
        if item.ref_id in shared
        and shared[item.ref_id][0].casefold() == item.name.casefold()
    }
    mitigations = tuple(
        item for item in all_mitigations if item.ref_id not in aliased_mitigations
    )
    known_mitigations = {item.ref_id for item in all_mitigations}

    technique_objects = {
        item.id: item
        for item in attack_data.get_techniques(remove_revoked_deprecated=True)
    }

    parents: dict[str, str] = {}
    for (
        stix_id,
        entries,
    ) in attack_data.get_all_parent_techniques_of_all_subtechniques().items():
        if stix_id not in technique_objects:
            continue
        parent_ref_ids = {
            get_external_reference(entry["object"])[0] for entry in entries
        }
        if len(parent_ref_ids) > 1:
            raise ValueError(
                f"Sub-technique {stix_id} has several parents: {sorted(parent_ref_ids)}"
            )
        parents[stix_id] = parent_ref_ids.pop()

    mitigated: dict[str, set[str]] = {}
    for (
        stix_id,
        entries,
    ) in attack_data.get_all_mitigations_mitigating_all_techniques().items():
        if stix_id not in technique_objects:
            continue
        for entry in entries:
            ref_id = get_external_reference(entry["object"])[0]
            if ref_id in known_mitigations:
                mitigated.setdefault(stix_id, set()).add(ref_id)

    groupings: dict[str, Grouping] = {}
    technique_groups: dict[str, set[str]] = {}
    if domain.grouping_dimension == "asset":
        assets = attack_data.get_all_assets_targeted_by_all_techniques()
        for stix_id, entries in assets.items():
            if stix_id not in technique_objects:
                continue
            for entry in entries:
                asset = entry["object"]
                if not is_active(asset):
                    continue
                name = str(asset.name).strip()
                ref_id = slugify(name)
                groupings.setdefault(ref_id, Grouping(ref_id=ref_id, name=name))
                technique_groups.setdefault(stix_id, set()).add(ref_id)
    else:
        for stix_id, item in technique_objects.items():
            for platform in getattr(item, "x_mitre_platforms", ()) or ():
                name = str(platform).strip()
                # ICS carries the literal "None"; never emit it as a facet
                if not name or name.casefold() == "none":
                    continue
                ref_id = slugify(name)
                groupings.setdefault(ref_id, Grouping(ref_id=ref_id, name=name))
                technique_groups.setdefault(stix_id, set()).add(ref_id)

    techniques = []
    for stix_id, item in technique_objects.items():
        record = to_attack_record(item)
        tactic_ref_ids = []
        for phase in getattr(item, "kill_chain_phases", ()) or ():
            ref_id = shortname_to_ref_id.get(phase.phase_name)
            if ref_id and ref_id not in tactic_ref_ids:
                tactic_ref_ids.append(ref_id)
        techniques.append(
            TechniqueRecord(
                ref_id=record.ref_id,
                name=record.name,
                description=record.description,
                parent_ref_id=parents.get(stix_id),
                tactic_ref_ids=tuple(tactic_ref_ids),
                groups=tuple(sorted(technique_groups.get(stix_id, ()))),
                mitigation_ref_ids=tuple(sorted(mitigated.get(stix_id, ()))),
            )
        )
    techniques.sort(key=lambda item: item.ref_id)

    return DomainContent(
        tactics=tactics,
        techniques=tuple(techniques),
        mitigations=mitigations,
        groupings=tuple(
            sorted(groupings.values(), key=lambda item: item.name.casefold())
        ),
        aliased_mitigations=aliased_mitigations,
        dependencies=(shared_library_urn,) if aliased_mitigations else (),
    )


# ---------------------------------------------------------------------------
# Translation carry-forward
# ---------------------------------------------------------------------------


def load_existing_translations(domain: DomainSpec) -> dict[str, dict[str, str]]:
    """Map urn -> {name, description} in French, from the shipped library."""
    path = domain.shipped_library
    if not path.exists():
        return {}

    with path.open(encoding="utf-8") as stream:
        library = yaml.safe_load(stream) or {}

    carried: dict[str, dict[str, str]] = {}

    def collect(entry: object) -> None:
        if not isinstance(entry, dict):
            return
        urn = entry.get("urn")
        french = (entry.get("translations") or {}).get("fr")
        if urn and isinstance(french, dict):
            values = {
                key: french[key] for key in ("name", "description") if french.get(key)
            }
            if values:
                carried[urn] = values

    french = (library.get("translations") or {}).get("fr")
    if isinstance(french, dict):
        carried[library.get("urn", domain.library_urn)] = {
            key: french[key] for key in ("name", "description") if french.get(key)
        }

    for entries in (library.get("objects") or {}).values():
        if isinstance(entries, list):
            for entry in entries:
                collect(entry)

    return carried


class TranslationSource:
    """French columns exist only when something can fill them.

    The library checker rejects a localized key with an empty value, so a
    domain with no translations gets no `[fr]` columns at all.
    """

    def __init__(
        self,
        carried: dict[str, dict[str, str]],
        emit_formulas: bool,
    ) -> None:
        self._carried = carried
        self._emit_formulas = emit_formulas
        self.carried_count = 0
        self.enabled = bool(carried) or emit_formulas

    def headers(self) -> tuple[str, ...]:
        return ("name[fr]", "description[fr]") if self.enabled else ()

    def cells(
        self,
        urn: str,
        name_cell: str,
        description_cell: str,
    ) -> tuple[object, ...]:
        if not self.enabled:
            return ()
        values = self._carried.get(urn)
        if values:
            self.carried_count += 1
            name = values.get("name")
            description = values.get("description")
            return (
                name or self._formula(name_cell),
                description or self._formula(description_cell),
            )
        return self._formula(name_cell), self._formula(description_cell)

    def _formula(self, cell: str) -> object:
        if not self._emit_formulas:
            return None
        return f'=TRADUIRE({cell},"en","fr")'


# ---------------------------------------------------------------------------
# Workbook generation
# ---------------------------------------------------------------------------


def style_meta_sheet(worksheet: Worksheet) -> None:
    for row in worksheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    worksheet.column_dimensions["A"].width = 24
    worksheet.column_dimensions["B"].width = 120


def style_content_sheet(
    worksheet: Worksheet,
    widths: Sequence[float],
) -> None:
    for cell in worksheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    for row in worksheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    # widths cover the translated layout; a sheet without French has fewer columns
    for column_index, width in enumerate(widths[: worksheet.max_column], start=1):
        column_letter = worksheet.cell(row=1, column=column_index).column_letter
        worksheet.column_dimensions[column_letter].width = width

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions


def append_meta_rows(
    worksheet: Worksheet,
    rows: Iterable[tuple[str, object]],
) -> None:
    for key, value in rows:
        worksheet.append((key, value))
    style_meta_sheet(worksheet)


def build_final_workbook(
    output: Path,
    domain: DomainSpec,
    version: str,
    description: str,
    copyright_text: str,
    content: DomainContent,
    translations: TranslationSource,
) -> None:
    workbook = Workbook()
    library_meta = workbook.active
    library_meta.title = LIBRARY_META_SHEET
    catalog_meta = workbook.create_sheet(CATALOG_META_SHEET)
    catalog_content = workbook.create_sheet(CATALOG_CONTENT_SHEET)
    groups_meta = workbook.create_sheet(GROUPS_META_SHEET)
    groups_content = workbook.create_sheet(GROUPS_CONTENT_SHEET)
    tactics_meta = workbook.create_sheet(TACTICS_META_SHEET)
    tactics_content = workbook.create_sheet(TACTICS_CONTENT_SHEET)
    mitigations_meta = workbook.create_sheet(MITIGATIONS_META_SHEET)
    mitigations_content = workbook.create_sheet(MITIGATIONS_CONTENT_SHEET)
    techniques_meta = workbook.create_sheet(TECHNIQUES_META_SHEET)
    techniques_content = workbook.create_sheet(TECHNIQUES_CONTENT_SHEET)

    library_name = f"{domain.title} v{version} - TTPs and Mitigations"
    library_rows: list[tuple[str, object]] = [
        ("type", "library"),
        ("urn", domain.library_urn),
        ("version", LIBRARY_VERSION),
        ("locale", LIBRARY_LOCALE),
        ("ref_id", domain.ref_id),
        ("name", library_name),
        ("description", description),
        ("copyright", copyright_text),
        ("provider", LIBRARY_PROVIDER),
        ("packager", LIBRARY_PACKAGER),
    ]
    if content.dependencies:
        library_rows.append(("dependencies", ", ".join(content.dependencies)))
    library_french = translations.cells(domain.library_urn, "B6", "B7")
    library_rows.extend(
        (key, value)
        for key, value in zip(translations.headers(), library_french)
        if value is not None
    )
    append_meta_rows(library_meta, library_rows)

    append_meta_rows(
        catalog_meta,
        (
            ("type", "ttp_catalog"),
            ("base_urn", "urn:intuitem:risk:ttp_catalog"),
            ("grouping_definition", GROUPING_BLOCK_NAME),
        ),
    )
    catalog_content.append(("ref_id", "name", "description", *translations.headers()))
    catalog_content.append(
        (
            domain.ref_id,
            domain.catalog_name,
            domain.catalog_description,
            *translations.cells(domain.catalog_urn, "B2", "C2"),
        )
    )
    style_content_sheet(catalog_content, (24, 48, 100, 48, 100))

    append_meta_rows(
        groups_meta,
        (("type", "ttp_groups"), ("name", GROUPING_BLOCK_NAME)),
    )
    groups_content.append(("ref_id", "name", "dimension"))
    for grouping in content.groupings:
        groups_content.append(
            (grouping.ref_id, grouping.name, domain.grouping_dimension)
        )
    style_content_sheet(groups_content, (32, 48, 18))

    append_meta_rows(
        tactics_meta,
        (
            ("type", "tactics"),
            ("base_urn", domain.tactics_base_urn),
            ("catalog_urn", domain.catalog_urn),
        ),
    )
    tactics_content.append(("ref_id", "name", "description", *translations.headers()))
    for row_number, item in enumerate(content.tactics, start=2):
        tactics_content.append(
            (
                item.ref_id,
                item.name,
                item.description,
                *translations.cells(
                    f"{domain.tactics_base_urn}:{item.ref_id.lower()}",
                    f"B{row_number}",
                    f"C{row_number}",
                ),
            )
        )
    style_content_sheet(tactics_content, (14, 48, 100, 48, 100))

    append_meta_rows(
        mitigations_meta,
        (("type", "reference_controls"), ("base_urn", domain.mitigations_base_urn)),
    )
    mitigations_content.append(
        (
            "ref_id",
            "name",
            "csf_function",
            "category",
            "description",
            *translations.headers(),
        )
    )
    missing_csf_mappings: list[str] = []
    for row_number, item in enumerate(content.mitigations, start=2):
        csf_function = domain.csf_functions.get(item.ref_id)
        if csf_function is None:
            csf_function = "protect"
            missing_csf_mappings.append(item.ref_id)
        mitigations_content.append(
            (
                item.ref_id,
                item.name,
                csf_function,
                "technical",
                item.description,
                *translations.cells(
                    f"{domain.mitigations_base_urn}:{item.ref_id.lower()}",
                    f"B{row_number}",
                    f"E{row_number}",
                ),
            )
        )
    style_content_sheet(mitigations_content, (14, 48, 18, 18, 100, 48, 100))

    append_meta_rows(
        techniques_meta,
        (
            ("type", "techniques"),
            ("base_urn", domain.techniques_base_urn),
            ("catalog_urn", domain.catalog_urn),
            ("tactics_base_urn", domain.tactics_base_urn),
        ),
    )
    techniques_content.append(
        (
            "ref_id",
            "name",
            "description",
            "parent_ref_id",
            "tactic_ref_ids",
            "groups",
            "reference_controls",
            *translations.headers(),
        )
    )
    for row_number, item in enumerate(content.techniques, start=2):
        techniques_content.append(
            (
                item.ref_id,
                item.name,
                item.description,
                item.parent_ref_id,
                ", ".join(item.tactic_ref_ids),
                ", ".join(item.groups),
                ", ".join(
                    content.aliased_mitigations.get(
                        ref_id, f"{domain.mitigations_base_urn}:{ref_id.lower()}"
                    )
                    for ref_id in item.mitigation_ref_ids
                ),
                *translations.cells(
                    f"{domain.techniques_base_urn}:{item.ref_id.lower()}",
                    f"B{row_number}",
                    f"C{row_number}",
                ),
            )
        )
    style_content_sheet(
        techniques_content,
        (14, 48, 100, 16, 24, 32, 48, 48, 100),
    )

    if missing_csf_mappings:
        refs = ", ".join(missing_csf_mappings)
        print(
            "⚠️  [WARNING] No preserved CSF function for "
            f"{refs}; defaulted to 'protect'.",
            file=sys.stderr,
        )

    temporary_output = output.with_name(f"{output.stem}.tmp.xlsx")
    temporary_output.unlink(missing_ok=True)
    try:
        workbook.save(temporary_output)
        temporary_output.replace(output)
    finally:
        workbook.close()
        temporary_output.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Cleanup and entry point
# ---------------------------------------------------------------------------


def cleanup(paths: Iterable[Path]) -> None:
    for path in paths:
        if path.exists():
            path.unlink()
            print(f'🗑️  [INFO] Deleted intermediate file: "{display_path(path)}"')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download MITRE ATT&CK data for one domain and build the versioned "
            "CISO Assistant Excel library."
        )
    )
    parser.add_argument(
        "-d",
        "--domain",
        choices=(*DOMAINS, "all"),
        default="enterprise",
        help="ATT&CK domain to build (default: enterprise)",
    )
    parser.add_argument(
        "-k",
        "--keep",
        action="store_true",
        help="keep the downloaded sources",
    )
    parser.add_argument(
        "--translation-formulas",
        action="store_true",
        help=(
            "fill untranslated French cells with =TRADUIRE() formulas to be "
            "evaluated in Excel"
        ),
    )
    return parser.parse_args()


def build_domain(
    session: requests.Session,
    domain: DomainSpec,
    description: str,
    copyright_text: str,
    emit_formulas: bool,
) -> tuple[Path, list[Path]]:
    downloaded: list[Path] = []

    version = get_attack_version(session, domain)
    print(f"✅ [OK] Detected ATT&CK {domain.commit_label} version: v{version}")

    download_file(session, domain.bundle_url, domain.local_bundle)
    downloaded.append(domain.local_bundle)

    content = extract_domain_content(domain.local_bundle, domain)
    print(f"✅ [OK] Retrieved {len(content.tactics)} tactics.")
    print(f"✅ [OK] Retrieved {len(content.techniques)} techniques.")
    print(f"✅ [OK] Retrieved {len(content.mitigations)} mitigations.")
    print(
        f"✅ [OK] Retrieved {len(content.groupings)} "
        f"{domain.grouping_dimension} groups."
    )
    if content.aliased_mitigations:
        refs = ", ".join(sorted(content.aliased_mitigations))
        print(
            f"ℹ️  [NOTE] {refs} already defined verbatim by "
            f"{', '.join(content.dependencies)}; referenced instead of redeclared."
        )

    carried = load_existing_translations(domain)
    translations = TranslationSource(carried, emit_formulas)
    if carried:
        print(
            f'ℹ️  [NOTE] Carrying French forward from "{display_path(domain.shipped_library)}" '
            f"({len(carried)} objects)."
        )

    output = SCRIPT_DIR / f"{domain.ref_id}-v{version}.xlsx"
    build_final_workbook(
        output=output,
        domain=domain,
        version=version,
        description=description,
        copyright_text=copyright_text,
        content=content,
        translations=translations,
    )
    if carried:
        print(f"✅ [OK] Carried {translations.carried_count} French translations.")
    print(f'✅ [OK] Created: "{display_path(output)}"')
    return output, downloaded


def main() -> None:
    args = parse_args()
    generated_intermediates: list[Path] = []
    outputs: list[tuple[str, Path]] = []

    selected = list(DOMAINS) if args.domain == "all" else [args.domain]

    try:
        with create_session() as session:
            print_step_banner(1, "Download shared MITRE source files")
            generated_intermediates.extend(download_shared_sources(session))

            print_step_banner(2, "Read shared release metadata")
            readme = README_PATH.read_text(encoding="utf-8")
            license_text = LICENSE_PATH.read_text(encoding="utf-8")
            description = build_library_description(readme)
            copyright_text = extract_attack_license(license_text)
            print("✅ [OK] Read the ATT&CK description and license.")

            for step, key in enumerate(selected, start=3):
                domain = DOMAINS[key]
                print_step_banner(step, f"Build the {domain.title} library")
                output, downloaded = build_domain(
                    session=session,
                    domain=domain,
                    description=description,
                    copyright_text=copyright_text,
                    emit_formulas=args.translation_formulas,
                )
                generated_intermediates.extend(downloaded)
                outputs.append((domain.title, output))

        print_step_banner(len(selected) + 3, "Summary")
        for title, output in outputs:
            print(f'- {title}: "{display_path(output)}"')
        if args.keep:
            print("ℹ️  [NOTE] Downloaded files were kept (--keep).")

    except KeyboardInterrupt:
        print("❌ [ERROR] Interrupted by user.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"❌ [ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        if not args.keep:
            cleanup(generated_intermediates)


if __name__ == "__main__":
    main()
