from bs4 import BeautifulSoup, NavigableString, Tag
import re
import pandas as pd
import string
import html
from urllib.parse import urlparse, unquote
import unicodedata
from tqdm import tqdm
from playwright.sync_api import sync_playwright


# ========= CONFIG =========
SOURCE_URL_FR = "https://www.cyber.gc.ca/fr/orientation/protection-linformation-designee-organisations-systemes-ne-relevant-pas-gouvernement-canada-itsp10171"
SOURCE_URL_EN = "https://www.cyber.gc.ca/en/guidance/protecting-specified-information-non-government-canada-systems-and-organizations-itsp10171"
OUTPUT_XLSX = "itsp.10.171_requirements.xlsx"
# ==========================

TOP_H2_RE = re.compile(r"^\s*(\d+)\s+(.*)$")
SECTION_H3_RE = re.compile(r"^\s*\d+\.\d+\s+")
REQ_H4_TEXT_RE = re.compile(r"^\s*(\d{2}\.\d{2}\.\d{2})\s+(.*)$")
FOOTNOTE_HREF_RE = re.compile(r"^#fn(\d+)$", re.IGNORECASE)

FR_NAME = "[ITSP.10.171] Protection de l’information désignée dans les organisations et les systèmes ne relevant pas du gouvernement du Canada"
EN_NAME = "[ITSP.10.171] Protecting specified information in non-Government of Canada systems and organizations"

FR_DESCRIPTION = """La protection de l’information désignée revêt une importance capitale pour les ministères et organismes du gouvernement du Canada (GC) et peut avoir une incidence directe sur la capacité du GC de réaliser ses missions et ses fonctions essentielles avec succès. Cette publication offre aux ministères et aux organismes du GC des exigences de sécurité recommandées afin de protéger la confidentialité de l’information désignée se trouvant dans des organisations et des systèmes ne relevant pas du GC. Ces exigences s’appliquent aux composants des systèmes ne relevant pas du GC qui gèrent, traitent, stockent ou transmettent de l’information désignée ou qui protègent de tels composants. Les exigences de sécurité sont destinées à l’usage des ministères et organismes du GC dans des contrats ou d’autres ententes établis avec des organisations ne relevant pas du GC.

Le présent document est une version canadienne de la publication du National Institute of Standards and Technology intitulée [NIST SP 800-171 Protecting Controlled Unclassified Information in Nonfederal Systems and Organizations (en anglais seulement)](https://csrc.nist.gov/pubs/sp/800/171/r3/final). Le Centre pour la cybersécurité produira une publication complémentaire à utiliser conjointement avec le document intitulé [NIST SP 800-171A Assessing Security Requirements for Controlled Unclassified Information (en anglais seulement)](https://csrc.nist.gov/pubs/sp/800/171/a/r3/final). Ce document fournira un ensemble complet de procédures pour évaluer les exigences de sécurité. Dans l’intervalle, le document NIST SP 800-171A (en anglais seulement) pourra servir de référence."""

EN_DESCRIPTION = """Protecting Specified Information is of paramount importance to Government of Canada (GC) departments and agencies and can directly impact the GC’s ability to successfully conduct its essential missions and functions. This publication provides GC departments and agencies with recommended security requirements for protecting the confidentiality of specified information when it resides in non-GC systems and organizations. These requirements apply to the components of non-GC systems that handle, process, store or transmit CI, or that provide protection for such components. The security requirements are intended for use by GC departments and agencies in contractual vehicles or other agreements established between those departments and agencies and non-GC organizations.

This publication is a Canadian version of the National Institute of Standards and Technology [NIST SP 800-171 Protecting Controlled Unclassified Information in Nonfederal Systems and Organizations](https://csrc.nist.gov/pubs/sp/800/171/r3/final). The Cyber Centre will produce a companion publication to use in conjunction with this publication, based on [NIST SP 800-171A Assessing Security Requirements for Controlled Unclassified Information](https://csrc.nist.gov/pubs/sp/800/171/a/r3/final). That publication will provide a comprehensive set of procedures to assess the security requirements. In the interim, NIST SP 800-171A can be used as a reference."""

LIBRARY_META_ROWS = [
    ("type", "library"),
    ("urn", "urn:intuitem:risk:library:itsp.10.171"),
    ("version", "1"),
    ("locale", "fr"),
    ("ref_id", "ITSP.10.171"),
    ("name", FR_NAME),
    ("description", FR_DESCRIPTION),
    (
        "copyright",
        "Centre de la sécurité des télécommunications Canada. "
        "[Open Government Licence - Canada]"
        "(https://open.canada.ca/fr/licence-du-gouvernement-ouvert-canada)",
    ),
    ("provider", "Centre de la sécurité des télécommunications Canada"),
    ("packager", "intuitem"),
    ("name[en]", EN_NAME),
    ("description[en]", EN_DESCRIPTION),
    (
        "copyright[en]",
        "Communications Security Establishment Canada. "
        "[Open Government Licence - Canada]"
        "(https://open.canada.ca/en/open-government-licence-canada)",
    ),
    ("provider[en]", "Communications Security Establishment Canada"),
]

FWK_META_ROWS = [
    ("type", "framework"),
    ("base_urn", "urn:intuitem:risk:req_node:itsp.10.171"),
    ("urn", "urn:intuitem:risk:framework:itsp.10.171"),
    ("ref_id", "ITSP.10.171"),
    ("name", FR_NAME),
    ("description", FR_DESCRIPTION),
    ("name[en]", EN_NAME),
    ("description[en]", EN_DESCRIPTION),
]


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def is_top_h2(tag: Tag) -> bool:
    return tag.name == "h2" and bool(
        TOP_H2_RE.match(clean_text(tag.get_text(" ", strip=True)))
    )


def is_section_h3(tag: Tag) -> bool:
    return tag.name == "h3" and bool(
        SECTION_H3_RE.match(clean_text(tag.get_text(" ", strip=True)))
    )


def is_requirement_h4(tag: Tag) -> bool:
    return tag.name == "h4" and bool(
        REQ_H4_TEXT_RE.match(clean_text(tag.get_text(" ", strip=True)))
    )


def normalize_inline_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def normalize_defn_id(value: str) -> str:
    return unicodedata.normalize("NFC", (value or "").strip())


def extract_href_fragment(href: str) -> str:
    href = (href or "").strip()
    parsed = urlparse(href)
    if parsed.fragment:
        return normalize_defn_id(unquote(parsed.fragment))
    if href.startswith("#"):
        return normalize_defn_id(unquote(href[1:]))
    m = re.search(r"#([^?#&]+)", href)
    if m:
        return normalize_defn_id(unquote(m.group(1)))
    return ""


def build_defn_abbr_html(definition_title: str) -> str:
    escaped_title = html.escape(definition_title or "", quote=True)
    return (
        f'<abbr title="{escaped_title}">'
        '<sup class="fa-solid fa-circle-question"></sup>'
        "</abbr>"
    )


def render_inline_markdown(
    node, note_refs: set[str], definitions_map: dict[str, str] | None = None
) -> str:
    active_definitions_map = definitions_map if definitions_map is not None else {}
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag):
        return ""
    if node.name == "br":
        return "\n"
    if node.get("id", "").startswith("defn-"):
        # Tooltip payload lives in hidden inline spans right after links; exclude from visible text.
        return ""

    if node.name == "a":
        href = (node.get("href") or "").strip()
        frag = extract_href_fragment(href)
        frag_key = frag if frag.startswith("defn-") else ""
        footnote_match = FOOTNOTE_HREF_RE.match(href)
        if footnote_match:
            footnote_num = footnote_match.group(1)
            note_refs.add(footnote_num)
            return f"[{footnote_num}]"
        if frag_key:
            definition_title = active_definitions_map.get(
                frag_key, active_definitions_map.get(frag_key.lower(), "")
            )
            return build_defn_abbr_html(definition_title)
        label = normalize_inline_text(
            "".join(
                render_inline_markdown(c, note_refs, active_definitions_map)
                for c in node.contents
            )
        )
        if not label:
            return ""
        if href.startswith("#") or href.lower().startswith("file://"):
            return f"**{label}**"
        if href:
            return f"[{label}]({href})"
        return label

    if node.name == "abbr":
        title = html.escape((node.get("title") or "").strip(), quote=True)
        label = normalize_inline_text(
            "".join(
                render_inline_markdown(c, note_refs, active_definitions_map)
                for c in node.contents
            )
        )
        return f'<abbr title="{title}">{label}</abbr>'

    return "".join(
        render_inline_markdown(c, note_refs, active_definitions_map)
        for c in node.contents
    )


def render_tag_text(
    tag: Tag,
    note_refs: set[str] | None = None,
    definitions_map: dict[str, str] | None = None,
) -> str:
    active_note_refs = note_refs if note_refs is not None else set()
    return normalize_inline_text(
        render_inline_markdown(tag, active_note_refs, definitions_map)
    )


def li_direct_text(
    li: Tag,
    note_refs: set[str] | None = None,
    definitions_map: dict[str, str] | None = None,
) -> str:
    parts = []
    active_note_refs = note_refs if note_refs is not None else set()
    for child in li.contents:
        if isinstance(child, NavigableString):
            t = clean_text(str(child))
            if t:
                parts.append(t)
        elif isinstance(child, Tag):
            if child.name in ("ol", "ul"):
                continue
            t = render_tag_text(child, active_note_refs, definitions_map)
            if t:
                parts.append(t)
    return clean_text(" ".join(parts))


def render_list_tag(
    list_tag: Tag,
    note_refs: set[str] | None = None,
    definitions_map: dict[str, str] | None = None,
) -> str:
    lines = []
    active_note_refs = note_refs if note_refs is not None else set()
    li_tags = list_tag.find_all("li", recursive=False)
    for idx, li in enumerate(li_tags, start=1):
        item_text = li_direct_text(li, active_note_refs, definitions_map) or clean_text(
            li.get_text(" ", strip=True)
        )
        if not item_text:
            continue
        if list_tag.name == "ol":
            lines.append(f"{idx}. {item_text}")
        else:
            lines.append(f"• {item_text}")
    return "\n".join(lines)


def render_block_tag(
    tag: Tag,
    note_refs: set[str] | None = None,
    definitions_map: dict[str, str] | None = None,
) -> tuple[str, str]:
    active_note_refs = note_refs if note_refs is not None else set()
    if tag.name == "p":
        return ("p", render_tag_text(tag, active_note_refs, definitions_map))
    if tag.name in ("ul", "ol"):
        return (tag.name, render_list_tag(tag, active_note_refs, definitions_map))
    if tag.name == "table":
        return ("table", render_tag_text(tag, active_note_refs, definitions_map))
    return ("", "")


def join_rendered_blocks(blocks: list[tuple[str, str]]) -> str:
    out = []
    prev_type = ""
    for block_type, text in blocks:
        if not text:
            continue
        if not out:
            out.append(text)
            prev_type = block_type
            continue

        # Before a list, insert a single newline. Otherwise keep a blank line.
        if block_type in ("ul", "ol"):
            out.append("\n" + text)
        elif prev_type in ("ul", "ol"):
            out.append("\n\n" + text)
        else:
            out.append("\n\n" + text)
        prev_type = block_type
    return "".join(out)


def add_row(rows, assessable, depth, ref_id, name, description):
    rows.append(
        {
            "assessable": assessable,
            "depth": depth,
            "ref_id": ref_id,
            "name": name,
            "description": description,
            "annotation": "",
        }
    )


def extract_disc_text(
    details_tag: Tag,
    note_refs: set[str],
    definitions_map: dict[str, str] | None = None,
) -> str:
    for h5 in details_tag.find_all("h5"):
        if clean_text(h5.get_text(" ", strip=True)).lower() == "discussion":
            disc_parts = []
            sib = h5.find_next_sibling()
            while sib is not None and not (isinstance(sib, Tag) and sib.name == "h5"):
                if isinstance(sib, Tag):
                    block_type, text = render_block_tag(sib, note_refs, definitions_map)
                    if text:
                        disc_parts.append((block_type, text))
                sib = sib.find_next_sibling()
            return join_rendered_blocks(disc_parts)
    return ""


def first_body_paragraph(
    details_tag: Tag,
    note_refs: set[str],
    definitions_map: dict[str, str] | None = None,
):
    for child in details_tag.children:
        if isinstance(child, Tag) and child.name == "summary":
            continue
        if isinstance(child, Tag) and child.name == "h5":
            break
        if isinstance(child, Tag) and child.name == "p":
            return render_tag_text(child, note_refs, definitions_map)
        if isinstance(child, Tag):
            p = child.find("p")
            if p:
                return render_tag_text(p, note_refs, definitions_map)
    return None


def extract_footnotes_map(
    soup: BeautifulSoup, definitions_map: dict[str, str] | None = None
) -> dict[str, str]:
    footnotes: dict[str, str] = {}
    for dd in soup.find_all("dd", id=True):
        match = re.match(r"^fn(\d+)$", dd.get("id", ""))
        if not match:
            continue
        footnote_num = match.group(1)
        blocks = []
        for child in dd.children:
            if not isinstance(child, Tag):
                continue
            if child.name == "p" and "fn-rtn" in child.get("class", []):
                continue
            block_type, text = render_block_tag(child, set(), definitions_map)
            if text:
                blocks.append((block_type, text))
        footnotes[footnote_num] = join_rendered_blocks(blocks)
    return footnotes


def extract_definitions_map(soup: BeautifulSoup) -> dict[str, str]:
    definitions: dict[str, str] = {}
    for node in soup.find_all(id=re.compile(r"^defn-")):
        node_id = normalize_defn_id(node.get("id", ""))
        if not node_id:
            continue
        # Prefer semantic blocks used by the page tooltip markup.
        title_span = node.find(class_="tooltip-h2")
        body_span = node.find(class_="tooltip-div")
        if title_span and body_span:
            first_text = clean_text(title_span.get_text(" ", strip=True))
            second_text = clean_text(body_span.get_text(" ", strip=True))
            definitions[node_id] = (
                f"{first_text}\n\n{second_text}"
                if first_text and second_text
                else first_text or second_text
            )
            definitions[node_id.lower()] = definitions[node_id]
            continue

        # Fallback: first two direct span children.
        child_spans = [c for c in node.find_all("span", recursive=False)]
        if len(child_spans) >= 2:
            first_text = clean_text(child_spans[0].get_text(" ", strip=True))
            second_text = clean_text(child_spans[1].get_text(" ", strip=True))
            definitions[node_id] = (
                f"{first_text}\n\n{second_text}"
                if first_text and second_text
                else first_text or second_text
            )
            definitions[node_id.lower()] = definitions[node_id]
            continue

        definitions[node_id] = clean_text(node.get_text(" ", strip=True))
        definitions[node_id.lower()] = definitions[node_id]
    return definitions


def build_annotation(note_refs: set[str], footnotes_map: dict[str, str]) -> str:
    if not note_refs:
        return ""
    parts = []
    for num in sorted(note_refs, key=lambda x: int(x)):
        text = footnotes_map.get(num, "")
        if text:
            parts.append(f"[{num}] {text}")
    return "\n\n".join(parts)


def parse_nested_list(
    nested_list: Tag,
    rows,
    base_req_id: str,
    alpha_label: str,
    num_path: list[int],
    depth: int,
    footnotes_map: dict[str, str],
    definitions_map: dict[str, str] | None = None,
):
    li_tags = [c for c in nested_list.children if isinstance(c, Tag) and c.name == "li"]
    for idx, li in enumerate(li_tags, start=1):
        note_refs = set()
        text = li_direct_text(li, note_refs, definitions_map) or clean_text(
            li.get_text(" ", strip=True)
        )
        full_path = [alpha_label] + num_path + [idx]
        ref_id = base_req_id + "." + ".".join(str(p) for p in full_path)
        add_row(rows, "x", depth, ref_id, "", text)
        rows[-1]["annotation"] = build_annotation(note_refs, footnotes_map)

        for sub in li.find_all(["ol", "ul"], recursive=False):
            parse_nested_list(
                sub,
                rows,
                base_req_id,
                alpha_label,
                num_path + [idx],
                depth + 1,
                footnotes_map,
                definitions_map,
            )


def fetch_html(
    url: str, timeout: int = 30, progress_label: str = "Downloading page"
) -> str:
    with tqdm(total=1, desc=progress_label, unit="page") as pbar:
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (compatible; ITSP10.171-Scraper/1.0)",
                locale="fr-CA",
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            page.wait_for_timeout(1500)
            html_content = page.content()
            context.close()
            browser.close()
            pbar.update(1)
    return html_content


def iter_elements_until(start_tag: Tag, stop_predicate):
    for el in start_tag.next_elements:
        if isinstance(el, Tag) and stop_predicate(el):
            break
        yield el


def collect_text(
    elements,
    note_refs: set[str],
    definitions_map: dict[str, str] | None = None,
) -> str:
    parts = []
    for el in elements:
        if isinstance(el, Tag):
            block_type, text = render_block_tag(el, note_refs, definitions_map)
            if text:
                parts.append((block_type, text))
    return join_rendered_blocks(parts)


def parse_requirement_detail(
    details_tag: Tag,
    rows,
    footnotes_map: dict[str, str],
    definitions_map: dict[str, str] | None = None,
):
    h4 = details_tag.find("h4", id=True)
    if not h4:
        return

    h4_txt = clean_text(h4.get_text(" ", strip=True))
    mm = REQ_H4_TEXT_RE.match(h4_txt)
    if not mm:
        return

    req_id = mm.group(1)
    req_title = clean_text(mm.group(2))
    add_row(rows, "", 3, req_id, req_title, "")

    alpha_list = None
    for ol in details_tag.find_all("ol"):
        cls = " ".join(ol.get("class", []))
        if "lst-upr-alph" in cls:
            alpha_list = ol
            break

    used_alpha = False
    if alpha_list:
        for idx, li in enumerate(alpha_list.find_all("li", recursive=False)):
            alpha = string.ascii_uppercase[idx]
            ref_a = f"{req_id}.{alpha}"
            note_refs = set()
            text = li_direct_text(li, note_refs, definitions_map) or clean_text(
                li.get_text(" ", strip=True)
            )
            add_row(rows, "x", 4, ref_a, "", text)
            rows[-1]["annotation"] = build_annotation(note_refs, footnotes_map)
            used_alpha = True

            for sub in li.find_all(["ol", "ul"], recursive=False):
                parse_nested_list(
                    sub, rows, req_id, alpha, [], 5, footnotes_map, definitions_map
                )

    if not used_alpha:
        note_refs = set()
        para = first_body_paragraph(details_tag, note_refs, definitions_map)
        if para:
            add_row(rows, "x", 4, f"{req_id}.A", "", para)
            rows[-1]["annotation"] = build_annotation(note_refs, footnotes_map)

    note_refs = set()
    disc = extract_disc_text(details_tag, note_refs, definitions_map)
    if disc:
        add_row(rows, "", 4, f"{req_id}.disc", "Discussion", disc)
        rows[-1]["annotation"] = build_annotation(note_refs, footnotes_map)


def parse_requirements_from_html(html: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "lxml")
    definitions_map = extract_definitions_map(soup)
    footnotes_map = extract_footnotes_map(soup, definitions_map)
    rows = []

    for h2 in soup.find_all("h2", id=True):
        if not is_top_h2(h2):
            continue

        h2_txt = clean_text(h2.get_text(" ", strip=True))
        h2_match = TOP_H2_RE.match(h2_txt)
        top_id = h2_match.group(1)
        top_name = clean_text(h2_match.group(2))

        top_note_refs = set()
        top_desc = collect_text(
            iter_elements_until(h2, lambda t: is_top_h2(t) or is_section_h3(t)),
            top_note_refs,
            definitions_map,
        )
        add_row(rows, "", 1, top_id, top_name, top_desc)
        rows[-1]["annotation"] = build_annotation(top_note_refs, footnotes_map)

        seen_h3 = set()
        for el in iter_elements_until(h2, lambda t: is_top_h2(t)):
            if not (isinstance(el, Tag) and is_section_h3(el)):
                continue

            h3 = el
            if id(h3) in seen_h3:
                continue
            seen_h3.add(id(h3))

            h3_txt = clean_text(h3.get_text(" ", strip=True))
            m = re.match(r"^\s*(\d+\.\d+)\s*(.*)$", h3_txt)
            if not m:
                continue

            sec_id, sec_name = m.group(1), clean_text(m.group(2))
            sec_note_refs = set()
            sec_desc = collect_text(
                iter_elements_until(
                    h3,
                    lambda t: (
                        is_top_h2(t)
                        or is_section_h3(t)
                        or t.name == "details"
                        or is_requirement_h4(t)
                    ),
                ),
                sec_note_refs,
                definitions_map,
            )
            add_row(rows, "", 2, sec_id, sec_name, sec_desc)
            rows[-1]["annotation"] = build_annotation(sec_note_refs, footnotes_map)

            for req_el in iter_elements_until(
                h3, lambda t: is_top_h2(t) or is_section_h3(t)
            ):
                if isinstance(req_el, Tag) and req_el.name == "details":
                    parse_requirement_detail(
                        req_el, rows, footnotes_map, definitions_map
                    )

    return pd.DataFrame(
        rows,
        columns=["assessable", "depth", "ref_id", "name", "description", "annotation"],
    )


def add_review_flag(df: pd.DataFrame) -> pd.DataFrame:
    def needs_review(desc):
        if pd.isna(desc):
            return ""
        return "x" if str(desc).rstrip().endswith(":") else ""

    df["review_flag"] = df["description"].apply(needs_review)
    return df


def build_meta_df(rows: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def build_excel_from_urls(
    source_url_fr: str = SOURCE_URL_FR,
    source_url_en: str = SOURCE_URL_EN,
    output_xlsx: str = OUTPUT_XLSX,
) -> str:
    html_fr = fetch_html(source_url_fr, progress_label="⤵️  Downloading [FR] page")
    html_en = fetch_html(source_url_en, progress_label="⤵️  Downloading [EN] page")

    df_fr = parse_requirements_from_html(html_fr)
    df_en = parse_requirements_from_html(html_en)[
        ["ref_id", "name", "description", "annotation"]
    ].rename(
        columns={
            "name": "name[en]",
            "description": "description[en]",
            "annotation": "annotation[en]",
        }
    )

    df = df_fr.merge(df_en, on="ref_id", how="left")
    df = df[
        [
            "assessable",
            "depth",
            "ref_id",
            "name",
            "description",
            "annotation",
            "name[en]",
            "description[en]",
            "annotation[en]",
        ]
    ]
    df = add_review_flag(df)

    library_meta_df = build_meta_df(LIBRARY_META_ROWS)
    fwk_meta_df = build_meta_df(FWK_META_ROWS)

    with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
        library_meta_df.to_excel(
            writer, index=False, header=False, sheet_name="library_meta"
        )
        fwk_meta_df.to_excel(writer, index=False, header=False, sheet_name="fwk_meta")
        df.to_excel(writer, index=False, sheet_name="fwk_content")

    return output_xlsx


def main():
    output_path = build_excel_from_urls()
    print(f'✅ Export complete: "{output_path}"')


if __name__ == "__main__":
    main()
