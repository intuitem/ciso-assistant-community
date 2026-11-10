import argparse
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Comment, NavigableString, Tag
from openpyxl import Workbook


# ========= CONFIG =========
BASE_URL = "https://www.cyber.gc.ca"
INDEX_URL_EN = (
    f"{BASE_URL}/en/guidance/cyber-security-privacy-risk-management/itsp10033"
)
INDEX_URL_FR = f"{BASE_URL}/fr/orientation/gestion-risques-lies-cybersecurite-risques-datteinte-vie-privee/itsp10033"
PROFILE_URL_EN = f"{BASE_URL}/en/guidance/cyber-security-privacy-risk-management/suggested-organizational-security-privacy-control-activity-profile-medium-impact-itsp10033-01"
PROFILE_URL_FR = f"{BASE_URL}/fr/orientation/gestion-risques-lies-cybersecurite-risques-datteinte-vie-privee/proposition-profil-dactivites-controles-organisationnels-securite-protection-vie-privee-incidence-moyenne-itsp10033-01"
OUTPUT_XLSX = "itsp.10.033.xlsx"
USER_AGENT = "Mozilla/5.0 (compatible; ITSP10.033-Scraper/1.0)"
# ==========================

CONTROL_H2_ID_RE = re.compile(r"^3\.\d+-[A-Z]{2}-\d+$")
CONTROL_H2_TEXT_RE = re.compile(r"^([A-Z]{2}-\d+)\s+(.*)$")
ENHANCEMENT_TITLE_RE = re.compile(r"^\((\d+)\)\s*(.*)$")
WITHDRAWN_RE = re.compile(r"^(Withdrawn|Annulé)\s*:", re.IGNORECASE)
EMPTY_SECTION_RE = re.compile(r"^(None|Aucun|Aucune|s\.o\.)\.?$", re.IGNORECASE)
BARE_EMAIL_RE = re.compile(r"^[^/@:\s]+@[^/@:\s]+$")

# Section headings (h3) and inline labels (strong) in both languages.
SECTION_KINDS = {
    "control": "statement",
    "controls": "statement",
    "activity": "statement",
    "activity/control": "statement",
    "contrôle": "statement",
    "contrôles": "statement",
    "activité": "statement",
    "discussion": "discussion",
    "gc discussion": "gc_discussion",
    "discussion au sein du gc": "gc_discussion",
    "related controls and activities": "related",
    "contrôles et activités connexes": "related",
    "enhancements": "enhancements",
    "améliorations": "enhancements",
    "references": "references",
    "références": "references",
}

# Labels written in the annotation. The source label is not reused: a few FR
# sections carry an English heading.
SECTION_LABELS = {
    "en": {
        "gc_discussion": "GC discussion",
        "related": "Related controls and activities",
        "references": "References",
    },
    "fr": {
        "gc_discussion": "Discussion au sein du GC",
        "related": "Contrôles et activités connexes",
        "references": "Références",
    },
}

EN_NAME = (
    "[ITSP.10.033] Security and privacy controls and assurance activities catalogue"
)
FR_NAME = "[ITSP.10.033] Catalogue des activités d’assurance et des contrôles de sécurité et de protection de la vie privée"

EN_DESCRIPTION = """This publication contains definitions of assurance activities and controls for systems and organizations that practitioners can use as a foundation for selecting, tailoring and allocating controls and assurance activities to manage cyber security and privacy risks. It is part of the Canadian Centre for Cyber Security series "Cyber security and privacy risk management: A lifecycle approach" and supersedes IT security risk management: A lifecycle approach (ITSG-33) Annex 3A – Security control catalogue.

To ensure a common baseline approach to risk management with the United States (US), the controls and assurance activities described in this publication align with [NIST SP 800-53 Rev. 5: Security and Privacy Controls for Information Systems and Organizations](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final). This publication is an adapted version of NIST SP 800-53, reflecting Canadian unique business and legislative requirements. All security and privacy controls, activities or enhancements starting at 400 (e.g., SA-400, IA-04(400)) are Canada-specific controls and activities."""

FR_DESCRIPTION = """Cette publication comporte des activités d’assurance et des contrôles pour les systèmes et les organisations sur lesquels peuvent se fonder les praticiennes et praticiens pour adapter et attribuer des contrôles et des activités d’assurance pour gérer des risques liés à la cybersécurité et des risques d’atteinte à la vie privée. Elle fait partie de la série du Centre canadien pour la cybersécurité « La gestion des risques liés à la cybersécurité et à la vie privée : Une méthode axée sur le cycle de vie » et remplace l’ITSG-33, Gestion des risques liés à la sécurité des TI : Une méthode axée sur le cycle de vie, Annexe 3A – Catalogue des contrôles de sécurité.

Pour assurer une approche commune de référence à l’égard de la gestion des risques avec les États-Unis, les contrôles et les activités d’assurance décrits dans la présente publication reflètent le contenu du document [NIST SP 800-53 Rev. 5: Security and Privacy Controls for Information Systems and Organizations (en anglais seulement)](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final). Cette publication est une version adaptée du document NIST SP 800-53, qui reflète les exigences législatives et opérationnelles particulières canadiennes. Tous les contrôles de sécurité et de protection de la vie privée, toutes les activités ou améliorations commençant à la valeur 400 (par exemple, SA-400, IA-04(400)) sont des contrôles et des activités propres au Canada."""

LIBRARY_META_ROWS = [
    ("type", "library"),
    ("urn", "urn:intuitem:risk:library:itsp.10.033"),
    ("version", "1"),
    ("locale", "en"),
    ("ref_id", "ITSP.10.033"),
    ("name", EN_NAME),
    ("description", EN_DESCRIPTION),
    (
        "copyright",
        "Communications Security Establishment Canada. "
        "[Open Government Licence - Canada]"
        "(https://open.canada.ca/en/open-government-licence-canada)",
    ),
    ("publication_date", "2026-03-31"),
    ("provider", "Communications Security Establishment Canada"),
    ("packager", "intuitem"),
    ("name[fr]", FR_NAME),
    ("description[fr]", FR_DESCRIPTION),
]

FWK_META_ROWS = [
    ("type", "framework"),
    ("base_urn", "urn:intuitem:risk:req_node:itsp.10.033"),
    ("urn", "urn:intuitem:risk:framework:itsp.10.033"),
    ("ref_id", "ITSP.10.033"),
    ("name", EN_NAME),
    ("description", EN_DESCRIPTION),
    ("implementation_groups_definition", "imp_grp"),
    ("name[fr]", FR_NAME),
    ("description[fr]", FR_DESCRIPTION),
]

IMP_GRP_META_ROWS = [
    ("type", "implementation_groups"),
    ("name", "imp_grp"),
]

IMP_GRP_HEADER = ["ref_id", "name", "description", "name[fr]", "description[fr]"]
IMP_GRP_ROWS = [
    [
        "medium",
        "Medium impact profile (ITSP.10.033-01)",
        "Controls, activities and enhancements selected in the Suggested organizational security and privacy control and activity profile - Medium impact (ITSP.10.033-01).",
        "Profil à incidence moyenne (ITSP.10.033-01)",
        "Contrôles, activités et améliorations sélectionnés dans la Proposition de profil d’activités et de contrôles organisationnels de sécurité et de protection de la vie privée – Incidence moyenne (ITSP.10.033-01).",
    ],
]

CONTENT_HEADER = [
    "assessable",
    "depth",
    "ref_id",
    "name",
    "description",
    "annotation",
    "implementation_groups",
    "name[fr]",
    "description[fr]",
    "annotation[fr]",
]

# ========= SOURCE FIXES =========
# The web pages carry defects that the PDF editions of the same publications
# do not have. They are fixed below, each one checked against the PDFs. A fix
# that no longer applies raises, so that a corrected page gets noticed.

# language: (url, caption prefix of the selection tables, "Selected" label)
PROFILE_PAGES = {
    "en": (PROFILE_URL_EN, "Table 4.", "Selected"),
    "fr": (PROFILE_URL_FR, "Tableau 4.", "Sélectionné"),
}

# (language, ref_id on the page, occurrence): actual ref_id
PROFILE_MISLABELLED_ROWS = {
    ("en", "CM-11(02)", 2): "CM-11(03)",
}

# Items the EN and FR profile pages disagree on. Both PDFs select them all.
PROFILE_OVERRIDES = {
    "AC-02(10)": True,  # not selected on the FR page
    "IA-02(12)": True,  # not selected on the EN page
    "PS-05": True,  # not selected on the EN page
    "PS-06": True,  # not selected on the FR page
    "SC-05(03)": True,  # not selected on the EN page
    "SC-07(03)": True,  # not selected on the FR page
    "SC-21": True,  # not selected on the FR page
    "SI-02(06)": True,  # not selected on the EN page
    "SI-07": True,  # not selected on the FR page
}

# (language, ref_id): (text of the first list item on the page, missing stem).
# The item holds its first sub-item instead of the stem, shifting the others.
MISSING_STEMS = {
    ("fr", "PL-02"): (
        "sont conformes à l’architecture d’entreprise de l’organisation",
        "Élaborer des plans de sécurité et de protection de la vie privée pour le système qui",
    ),
}

FR_CA_02_MISSING_PARAGRAPH = "Les organisations évaluent les contrôles dans les systèmes et les environnements dans lesquels ces systèmes fonctionnent dans le cadre des autorisations initiales ou continues du système, de la surveillance continue, de la conception et du développement des systèmes, de l’ingénierie de la sécurité et de la protection de la vie privée des systèmes, et du cycle de développement des systèmes comme il est recommandé dans les documents Activités organisationnelles de gestion des risques pour la cybersécurité et la vie privée (ITSP.10.036) et Activités de gestion des risques pour la cybersécurité et la vie privée tout au long du cycle de vie des systèmes (ITSP.10.037). Les évaluations aident à assurer que les organisations respectent les exigences de sécurité et de protection de la vie privée, à identifier les faiblesses et les lacunes dans le processus de conception et de développement du système, et à fournir les renseignements essentiels nécessaires pour prendre des décisions en fonction des risques dans le cadre des processus d’autorisation, et assurer le respect des procédures d’atténuation des vulnérabilités."

EN_PM_30_DUPLICATED_SENTENCE = " An organization-wide supply chain risk management strategy includes an unambiguous expression of the supply chain risk appetite and tolerance for the organization, acceptable supply chain risk mitigation strategies or controls, a process for consistently evaluating and monitoring supply chain risk, approaches for implementing and communicating the supply chain risk management strategy, and the associated roles and responsibilities."

# (language, ref_id, field, text on the page, text in the PDF)
SOURCE_CORRECTIONS = [
    # Statement of another enhancement.
    (
        "en",
        "SC-18(02)",
        "description",
        "Prevent the download and execution of [Assignment: organization-defined unacceptable mobile code].",
        "Verify that the acquisition, development, and use of mobile code to be deployed in the system meets [Assignment: organization-defined mobile code requirements].",
    ),
    # Dropped or garbled words.
    ("en", "AC-02", "description", "personnel orroles]", "personnel or roles]"),
    (
        "en",
        "AC-11",
        "description",
        "organization-defined tie period]",
        "organization-defined time period]",
    ),
    (
        "en",
        "AC-02(01)",
        "description",
        "Support of system accounts",
        "Support the management of system accounts",
    ),
    ("en", "AC-19", "annotation", "for sireless local", "for wireless local"),
    ("en", "RA-08", "annotation", "the rivacy ActP.", "the Privacy Act."),
    ("en", "SC-42", "annotation", "for nobile device", "for mobile device"),
    ("en", "SI-19", "annotation", "and Governan]", "and Governance]"),
    ("fr", "SI-19(01)", "name", ": Collection", ": Collecte"),
    ("fr", "MA-05", "annotation", "[SCAP, Manuel", "[SPAC, Manuel"),
    ("fr", "SC-401", "description", "CNSSI , ou", "CNSSI 5006, ou"),
    # Sentence repeated twice.
    (
        "en",
        "PM-30",
        "annotation",
        "roles and responsibilities." + EN_PM_30_DUPLICATED_SENTENCE,
        "roles and responsibilities.",
    ),
    # Unmarked section label, missing subject.
    (
        "en",
        "PM-26",
        "annotation",
        "GC discussion: departments and agencies are required",
        "**GC discussion:** GC departments and agencies are required",
    ),
    # Related controls: missing, or belonging to the previous enhancement.
    (
        "en",
        "PT-05(02)",
        "annotation",
        "the notice provisions of the Privacy Act.",
        "the notice provisions of the Privacy Act.\n\n**Related controls and activities:** PT-06.",
    ),
    (
        "fr",
        "SI-04(25)",
        "annotation",
        "l’analyse du trafic.\n\n**Contrôles et activités connexes :** AC-18.",
        "l’analyse du trafic.",
    ),
    # Missing discussion paragraph.
    (
        "fr",
        "CA-02",
        "annotation",
        "est nécessaire pour effectuer les EFVP.",
        "est nécessaire pour effectuer les EFVP.\n\n" + FR_CA_02_MISSING_PARAGRAPH,
    ),
    # Text left in English on the FR pages.
    (
        "fr",
        "PE-18(01)",
        "description",
        "Withdrawn: Moved to PE-23.",
        "Annulé : Transféré sous le contrôle PE-23.",
    ),
    (
        "fr",
        "PS-06(03)",
        "annotation",
        "Organizations comply with applicable laws, Orders in Council, directives, regulations, policies, standards, and guidelines regarding matters of post-employment requirements on terminated individuals.",
        "Les organisations se conforment aux lois, aux décrets, aux directives, à la réglementation, aux politiques, aux normes et aux lignes directrices applicables pour ce qui est des exigences régissant l’après-mandat des personnes ayant quitté leur emploi.",
    ),
    (
        "fr",
        "SA-400(07)",
        "name",
        "Sovereignty and jurisdiction: Protection against extraterritorial compulsion",
        "Souveraineté et juridiction : Protection contre les contraintes extraterritoriales",
    ),
    (
        "fr",
        "SI-07(08)",
        "name",
        "Firmware and information integrity:",
        "Intégrité des micrologiciels et de l’information :",
    ),
    (
        "fr",
        "MA-04(02)",
        "description",
        "au contrôle MA-01 and MA-04.",
        "aux contrôles MA-01 et MA-04.",
    ),
    (
        "fr",
        "PE-07",
        "description",
        "au contrôle PE-02 and PE-03.",
        "aux contrôles PE-02 et PE-03.",
    ),
    (
        "fr",
        "SA-06",
        "description",
        "au contrôle CM-10 and SI-07.",
        "aux contrôles CM-10 et SI-07.",
    ),
    (
        "fr",
        "SA-07",
        "description",
        "au contrôle CM-11 and SI-07.",
        "aux contrôles CM-11 et SI-07.",
    ),
    (
        "fr",
        "SA-12(13)",
        "description",
        "au contrôle MA-06 and RA-09.",
        "aux contrôles MA-06 et RA-09.",
    ),
    (
        "fr",
        "SA-12(14)",
        "description",
        "sous le contrôle SR-04(01) and SR-04(02).",
        "sous les contrôles SR-04(01) et SR-04(02).",
    ),
    # Defects that the FR PDF shares, fixed after the EN text.
    ("fr", "AU-06", "annotation", "SI-04 et-07.", "SI-04 et SI-07."),
    (
        "fr",
        "AC-06(07)",
        "description",
        "Examiner les [Affectation : droits d’accès attribués",
        "Examiner les droits d’accès attribués",
    ),
    (
        "fr",
        "SI-04(22)",
        "description",
        "b. Sélection (un choix ou plus) : Vérifier; Alerter [Affectation : personnel ou rôles définis par l’organisation] lorsqu’une",
        "b. [Sélection (un choix ou plus) : Vérifier; Alerter [Affectation : personnel ou rôles définis par l’organisation]] lorsqu’une",
    ),
]
# ================================


def fetch_html(url: str, retries: int = 5) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                html = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as error:
            if isinstance(error, urllib.error.HTTPError) and error.code < 500:
                raise
            print(f"⚠️  [WARNING] {url}: {error}, retrying")
            html = ""
        main = BeautifulSoup(html, "lxml").find("main")
        # The site sometimes serves an empty page shell under load: retry.
        if main is not None and main.find("h1") is not None:
            return html
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"No usable page after {retries} attempts: {url}")


def clean_text(text: str) -> str:
    text = (text or "").replace("\xa0", " ").replace(" ", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def section_kind(label: str) -> str | None:
    key = clean_text(label).rstrip(" :").strip().lower()
    return SECTION_KINDS.get(key)


def list_label(style: str, number: int) -> str:
    if style == "decimal":
        return str(number)
    # Spreadsheet-style letters, as browsers render them: 27 -> AA, 54 -> BB.
    label = ""
    while number:
        number, rest = divmod(number - 1, 26)
        label = chr(65 + rest) + label
    return label if style == "upper" else label.lower()


def list_style(list_tag: Tag) -> str:
    if list_tag.name == "ul":
        return "bullet"
    classes = list_tag.get("class") or []
    if "lst-upr-alph" in classes:
        return "upper"
    if "lst-lwr-alph" in classes:
        return "lower"
    return "decimal"


def render_inline(node: Tag, skip_lists: bool = False) -> str:
    parts = []
    for child in node.children:
        if isinstance(child, Comment):
            continue
        if isinstance(child, NavigableString):
            parts.append(str(child))
            continue
        if not isinstance(child, Tag):
            continue
        if child.name in ("ol", "ul"):
            if not skip_lists:
                parts.append("\n" + "\n".join(render_list(child)) + "\n")
        elif child.name == "br":
            parts.append("\n")
        elif child.name == "a":
            label = render_inline(child).strip()
            href = (child.get("href") or "").strip()
            if BARE_EMAIL_RE.match(href):
                # An address used as href would resolve to a page of the site.
                href = f"mailto:{href}"
            if label and href and not href.startswith("#"):
                parts.append(f"[{label}]({urljoin(BASE_URL, href)})")
            else:
                parts.append(label)
        elif child.name == "strong":
            label = render_inline(child).strip()
            parts.append(f"**{label}**" if label else "")
        else:
            parts.append(render_inline(child, skip_lists))
    return clean_text("".join(parts))


def render_list(list_tag: Tag, parent_label: str = "") -> list[str]:
    """Render a list as plain lines. Items get hierarchical labels (A., A.1.,
    a.) matching how the catalogue cites them (e.g. AT-02A.1); markdown list
    markers are avoided so that the renderer keeps the source numbering."""
    lines = []
    style = list_style(list_tag)
    number = int(list_tag.get("start") or 1)
    for li in list_tag.find_all("li", recursive=False):
        text = render_inline(li, skip_lists=True)
        if style == "bullet":
            label = parent_label
            if text:
                lines.append(f"• {text}")
        else:
            own = list_label(style, number)
            label = f"{parent_label}.{own}" if parent_label else own
            if text:
                lines.append(f"{label}. {text}")
            number += 1
        for sub in li.find_all(["ol", "ul"], recursive=False):
            lines.extend(render_list(sub, label))
    return lines


def render_block(tag: Tag) -> str:
    if tag.name in ("ol", "ul"):
        return "\n".join(render_list(tag))
    if tag.name in ("p", "table", "dl", "figure", "blockquote"):
        return render_inline(tag)
    return ""


def leading_label(tag: Tag) -> tuple[Tag | None, str | None]:
    """The section label a paragraph or list item starts with, and its kind."""
    first = next(
        (
            c
            for c in tag.children
            if not (isinstance(c, NavigableString) and not c.strip())
        ),
        None,
    )
    if isinstance(first, Tag) and first.name == "strong":
        kind = section_kind(first.get_text(" ", strip=True))
        if kind is not None:
            return first, kind
    return None, None


def strip_statement_label(tag: Tag) -> str:
    """Render a paragraph, dropping a leading "Control:"-style label."""
    label_tag, kind = leading_label(tag)
    if kind == "statement":
        label_tag.extract()
    return render_inline(tag)


def labelled(kind: str, text: str, lang: str, block: bool = False) -> str:
    colon = " :" if lang == "fr" else ":"
    separator = "\n" if block else " "
    return f"**{SECTION_LABELS[lang][kind]}{colon}**{separator}{text}"


def control_sections(h2: Tag) -> list[Tag]:
    elements = []
    for sibling in h2.find_next_siblings():
        if sibling.name in ("h2", "hr"):
            break
        elements.append(sibling)
    return elements


def restore_missing_stem(h2: Tag, lang: str, ref_id: str) -> None:
    """Give a statement back the stem its first list item lost on the page."""
    if (lang, ref_id) not in MISSING_STEMS:
        return
    orphan, stem = MISSING_STEMS[(lang, ref_id)]
    top = next((e for e in control_sections(h2) if e.name == "ol"), None)
    item = top.find("li", recursive=False) if top else None
    nested = item.find("ol", recursive=False) if item else None
    if nested is None or render_inline(item, skip_lists=True) != orphan:
        raise ValueError(
            f"{lang} {ref_id}: the missing stem fix no longer applies, "
            "check the page and update MISSING_STEMS"
        )
    first = Tag(name="li")
    for child in reversed(list(nested.previous_siblings)):
        first.append(child.extract())
    nested.insert(0, first)
    item.insert(0, stem)


def parse_enhancements(list_tag: Tag, control_ref: str, lang: str) -> list[dict]:
    enhancements = []
    for li in list_tag.find_all("li", recursive=False):
        # Usually "<strong>(01) Title</strong>", sometimes "(400) <strong>Title</strong>".
        title = "".join(
            c.get_text() if isinstance(c, Tag) else str(c)
            for c in li.children
            if not (isinstance(c, Tag) and c.name in ("ul", "ol"))
            and not isinstance(c, Comment)
        )
        match = ENHANCEMENT_TITLE_RE.match(clean_text(title))
        if not match:
            raise ValueError(f"{control_ref}: unexpected enhancement markup: {li}")
        statement, discussion, notes = [], [], []
        section = "statement"
        for inner in li.find_all(["ul", "ol"], recursive=False):
            for item in inner.find_all("li", recursive=False):
                # An item without a label continues the section it follows.
                label_tag, kind = leading_label(item)
                if label_tag is not None:
                    label_tag.extract()
                    section = kind
                if section == "statement":
                    lines = [render_inline(item, skip_lists=True)] + [
                        line
                        for sub in item.find_all(["ol", "ul"], recursive=False)
                        for line in render_list(sub)
                    ]
                    statement.append("\n".join(line for line in lines if line))
                    continue
                text = render_inline(item)
                if not text or EMPTY_SECTION_RE.match(text):
                    continue
                if section == "discussion":
                    discussion.append(text)
                elif label_tag is not None:
                    notes.append(labelled(section, text, lang))
                else:
                    notes.append(text)
        description = "\n\n".join(part for part in statement if part)
        enhancements.append(
            {
                "ref_id": f"{control_ref}({match.group(1)})",
                "name": clean_text(match.group(2)),
                "description": description,
                "annotation": "\n\n".join(discussion + notes),
                "withdrawn": bool(WITHDRAWN_RE.match(description)),
            }
        )
    return enhancements


def parse_control(h2: Tag, lang: str) -> dict:
    match = CONTROL_H2_TEXT_RE.match(clean_text(h2.get_text()))
    if not match:
        raise ValueError(f"Unexpected control heading: {h2}")
    ref_id, name = match.group(1), clean_text(match.group(2))
    restore_missing_stem(h2, lang, ref_id)

    # Group the section's elements under their h3 heading; content before the
    # first heading is the statement (some controls use an inline label).
    groups: list[tuple[str, list[Tag]]] = [("statement", [])]
    for element in control_sections(h2):
        label = element.get_text(" ", strip=True)
        label_tag, inline_kind = leading_label(element)
        if element.name == "h3":
            kind = section_kind(label)
            if kind is None:
                raise ValueError(f"{ref_id}: unknown section heading {label!r}")
            groups.append((kind, []))
        elif element.name == "p" and section_kind(label) is not None:
            # A few sections use a paragraph ("References:") as their heading.
            groups.append((section_kind(label), []))
        elif element.name == "p" and inline_kind not in (None, "statement"):
            # Or start with their label ("Enhancements: None").
            label_tag.extract()
            groups.append((inline_kind, [element]))
        elif element.name == "div" and "clearfix" in (element.get("class") or []):
            continue
        elif element.name == "div" and "pull-right" in (element.get("class") or []):
            continue
        else:
            groups[-1][1].append(element)

    statement, discussion, notes, enhancements = [], [], [], []
    previous_is_list = False
    for kind, elements in groups:
        if kind == "statement":
            for element in elements:
                is_list = element.name in ("ol", "ul")
                text = (
                    render_block(element) if is_list else strip_statement_label(element)
                )
                if not text:
                    continue
                # Canadian specifications (AA., BB.) are separate lists: keep
                # them in the same block as the items they follow.
                if is_list and previous_is_list:
                    statement[-1] += "\n" + text
                else:
                    statement.append(text)
                previous_is_list = is_list
        elif kind == "enhancements":
            for element in elements:
                if element.name in ("ul", "ol"):
                    enhancements.extend(parse_enhancements(element, ref_id, lang))
        else:
            text = "\n\n".join(t for t in map(render_block, elements) if t)
            if not text or EMPTY_SECTION_RE.match(text):
                continue
            if kind == "discussion":
                discussion.append(text)
            else:
                notes.append(labelled(kind, text, lang, block=kind == "references"))

    description = "\n\n".join(statement)
    return {
        "ref_id": ref_id,
        "name": name,
        "description": description,
        "annotation": "\n\n".join(discussion + notes),
        "withdrawn": bool(WITHDRAWN_RE.match(description)),
        "enhancements": enhancements,
    }


def parse_family_page(html: str, lang: str) -> dict | None:
    main = BeautifulSoup(html, "lxml").find("main")
    control_h2s = main.find_all("h2", id=CONTROL_H2_ID_RE)
    if not control_h2s:
        return None
    controls = [parse_control(h2, lang) for h2 in control_h2s]
    intro = []
    for element in main.find("h1").find_all_next():
        if element is control_h2s[0]:
            break
        if element.name == "p" and element.find_parent(["ul", "ol", "nav"]) is None:
            text = render_inline(element)
            if text:
                intro.append(text)
    return {
        "ref_id": controls[0]["ref_id"].split("-")[0],
        "name": clean_text(main.find("h1").get_text()),
        "description": "\n\n".join(intro),
        "annotation": "",
        "controls": controls,
    }


def family_page_urls(index_html: str) -> list[str]:
    main = BeautifulSoup(index_html, "lxml").find("main")
    urls = []
    for a in main.find_all("a", href=True):
        url = urljoin(BASE_URL, a["href"].split("#")[0])
        if "/itsp10033/" in url and url not in urls:
            urls.append(url)
    return urls


def scrape_catalogue(index_url: str, lang: str) -> list[dict]:
    families = []
    for url in family_page_urls(fetch_html(index_url)):
        family = parse_family_page(fetch_html(url), lang)
        if family is not None:
            print(f"   > [{lang.upper()}] {family['ref_id']}: {family['name']}")
            families.append(family)
        time.sleep(0.5)
    return families


def scrape_profile_selection(lang: str) -> dict[str, bool]:
    """Map each item of the profile's selection tables to its selected status."""
    url, caption_prefix, selected_label = PROFILE_PAGES[lang]
    main = BeautifulSoup(fetch_html(url), "lxml").find("main")
    statuses: dict[str, bool] = {}
    occurrences: dict[str, int] = {}
    for table in main.find_all("table"):
        caption = table.find("caption")
        if not caption or not clean_text(caption.get_text(" ", strip=True)).startswith(
            caption_prefix
        ):
            continue
        for tr in table.find("tbody").find_all("tr"):
            cells = [
                clean_text(c.get_text(" ", strip=True))
                for c in tr.find_all(["td", "th"])
            ]
            if len(cells) <= 5:
                continue
            ref_id = f"{cells[0]}-{cells[1]}"
            occurrences[ref_id] = occurrences.get(ref_id, 0) + 1
            ref_id = PROFILE_MISLABELLED_ROWS.get(
                (lang, ref_id, occurrences[ref_id]), ref_id
            )
            if ref_id in statuses:
                raise ValueError(f"{lang.upper()} profile lists {ref_id} twice")
            statuses[ref_id] = cells[5] == selected_label
    if not any(statuses.values()):
        raise ValueError(f"No selected item found in the {lang.upper()} profile")
    for page_lang, ref_id, occurrence in PROFILE_MISLABELLED_ROWS:
        if page_lang == lang and occurrences.get(ref_id, 0) < occurrence:
            raise ValueError(
                f"{lang.upper()} profile: {ref_id} is no longer mislabelled, "
                "update PROFILE_MISLABELLED_ROWS"
            )
    return statuses


def merge_profile_selections(en: dict[str, bool], fr: dict[str, bool]) -> set[str]:
    for ref_id in sorted(set(en) ^ set(fr)):
        only = "EN" if ref_id in en else "FR"
        print(f"⚠️  [WARNING] {ref_id} is only listed in the {only} profile")
    disputed = {ref_id for ref_id in set(en) & set(fr) if en[ref_id] != fr[ref_id]}
    if disputed != set(PROFILE_OVERRIDES):
        raise ValueError(
            "EN/FR profile disagreements differ from PROFILE_OVERRIDES: "
            f"undocumented {sorted(disputed - set(PROFILE_OVERRIDES))}, "
            f"settled {sorted(set(PROFILE_OVERRIDES) - disputed)}"
        )
    merged = {**fr, **en, **PROFILE_OVERRIDES}
    return {ref_id for ref_id, is_selected in merged.items() if is_selected}


def apply_source_corrections(rows: dict[str, dict], lang: str) -> None:
    for correction_lang, ref_id, field, old, new in SOURCE_CORRECTIONS:
        if correction_lang != lang:
            continue
        text = rows[ref_id][field]
        if text.count(old) != 1:
            raise ValueError(
                f"{lang} {ref_id} {field}: correction no longer applies "
                f"({old[:60]!r}), check the page and update SOURCE_CORRECTIONS"
            )
        rows[ref_id][field] = text.replace(old, new)


def flatten(families: list[dict]) -> list[dict]:
    rows = []
    for family in families:
        rows.append({**family, "depth": 1, "assessable": False})
        for control in family["controls"]:
            rows.append({**control, "depth": 2, "assessable": not control["withdrawn"]})
            for enhancement in control["enhancements"]:
                rows.append(
                    {
                        **enhancement,
                        "depth": 3,
                        "assessable": not enhancement["withdrawn"],
                    }
                )
    return rows


def write_key_value_sheet(workbook: Workbook, title: str, rows) -> None:
    sheet = workbook.create_sheet(title)
    for row in rows:
        sheet.append(list(row))


def build_excel(output_xlsx: str = OUTPUT_XLSX) -> str:
    print("⌛ Downloading [EN] catalogue...")
    rows_en = flatten(scrape_catalogue(INDEX_URL_EN, "en"))
    print("⌛ Downloading [FR] catalogue...")
    rows_fr = {
        row["ref_id"]: row for row in flatten(scrape_catalogue(INDEX_URL_FR, "fr"))
    }
    print("⌛ Downloading [EN] and [FR] medium impact profile (ITSP.10.033-01)...")
    selected = merge_profile_selections(
        scrape_profile_selection("en"), scrape_profile_selection("fr")
    )

    refs_en = [row["ref_id"] for row in rows_en]
    if len(refs_en) != len(set(refs_en)):
        raise ValueError("Duplicate ref_id in the EN catalogue")
    if set(refs_en) != set(rows_fr):
        raise ValueError(
            f"EN/FR mismatch: EN only {sorted(set(refs_en) - set(rows_fr))}, "
            f"FR only {sorted(set(rows_fr) - set(refs_en))}"
        )
    if selected - set(refs_en):
        raise ValueError(
            f"Profile selects unknown items: {sorted(selected - set(refs_en))}"
        )
    apply_source_corrections({row["ref_id"]: row for row in rows_en}, "en")
    apply_source_corrections(rows_fr, "fr")
    assessable = {row["ref_id"] for row in rows_en if row["assessable"]}
    if withdrawn := selected - assessable:
        # e.g. the profile selects AC-02(10) although the catalogue withdrew
        # it: it cannot be assessed, so leave it out.
        print(
            f"⚠️  [WARNING] Profile selects withdrawn items, skipped: {sorted(withdrawn)}"
        )
        selected -= withdrawn

    workbook = Workbook()
    workbook.remove(workbook.active)
    write_key_value_sheet(workbook, "library_meta", LIBRARY_META_ROWS)
    write_key_value_sheet(workbook, "fwk_meta", FWK_META_ROWS)
    content = workbook.create_sheet("fwk_content")
    content.append(CONTENT_HEADER)
    for row in rows_en:
        fr = rows_fr[row["ref_id"]]
        content.append(
            [
                "x" if row["assessable"] else "",
                row["depth"],
                row["ref_id"],
                row["name"],
                row["description"] or None,
                row["annotation"] or None,
                "medium" if row["ref_id"] in selected else None,
                fr["name"],
                fr["description"] or None,
                fr["annotation"] or None,
            ]
        )
    write_key_value_sheet(workbook, "imp_grp_meta", IMP_GRP_META_ROWS)
    write_key_value_sheet(workbook, "imp_grp_content", [IMP_GRP_HEADER, *IMP_GRP_ROWS])
    workbook.save(output_xlsx)

    print(
        f"   > {len(rows_en)} nodes, {len(assessable)} assessable, "
        f"{len(selected)} in the medium impact profile"
    )
    return output_xlsx


def main():
    parser = argparse.ArgumentParser(
        description="Scrape ITSP.10.033 (EN/FR) and its medium impact profile into a framework Excel."
    )
    parser.add_argument(
        "-o",
        "--output",
        default=OUTPUT_XLSX,
        help=f"Output Excel file path (default: {OUTPUT_XLSX})",
    )
    args = parser.parse_args()
    print(f'✅ Export complete: "{build_excel(args.output)}"')


if __name__ == "__main__":
    main()
