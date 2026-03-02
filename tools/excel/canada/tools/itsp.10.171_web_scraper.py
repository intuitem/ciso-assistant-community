from bs4 import BeautifulSoup, NavigableString, Tag
import re
import pandas as pd
import string
import requests
from tqdm import tqdm

# ========= CONFIG =========
SOURCE_URL_FR = "https://www.cyber.gc.ca/fr/orientation/protection-linformation-designee-organisations-systemes-ne-relevant-pas-gouvernement-canada-itsp10171"
SOURCE_URL_EN = "https://www.cyber.gc.ca/en/guidance/protecting-specified-information-non-government-canada-systems-and-organizations-itsp10171"
OUTPUT_XLSX = "itsp.10.171_requirements.xlsx"
# ==========================

TOP_H2_RE = re.compile(r"^\s*(\d+)\s+(.*)$")
SECTION_H3_RE = re.compile(r"^\s*\d+\.\d+\s+")
REQ_H4_TEXT_RE = re.compile(r"^\s*(\d{2}\.\d{2}\.\d{2})\s+(.*)$")


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


def li_direct_text(li: Tag) -> str:
    parts = []
    for child in li.contents:
        if isinstance(child, NavigableString):
            t = clean_text(str(child))
            if t:
                parts.append(t)
        elif isinstance(child, Tag):
            if child.name in ("ol", "ul"):
                continue
            t = clean_text(child.get_text(" ", strip=True))
            if t:
                parts.append(t)
    return clean_text(" ".join(parts))


def add_row(rows, assessable, depth, ref_id, name, description):
    rows.append(
        {
            "assessable": assessable,
            "depth": depth,
            "ref_id": ref_id,
            "name": name,
            "description": description,
        }
    )


def extract_disc_text(details_tag: Tag) -> str:
    for h5 in details_tag.find_all("h5"):
        if clean_text(h5.get_text(" ", strip=True)).lower() == "discussion":
            disc_parts = []
            sib = h5.find_next_sibling()
            while sib is not None and not (isinstance(sib, Tag) and sib.name == "h5"):
                if isinstance(sib, Tag):
                    disc_parts.append(sib.get_text(" ", strip=True))
                sib = sib.find_next_sibling()
            return clean_text(" ".join(disc_parts))
    return ""


def first_body_paragraph(details_tag: Tag):
    for child in details_tag.children:
        if isinstance(child, Tag) and child.name == "summary":
            continue
        if isinstance(child, Tag) and child.name == "h5":
            break
        if isinstance(child, Tag) and child.name == "p":
            return clean_text(child.get_text(" ", strip=True))
        if isinstance(child, Tag):
            p = child.find("p")
            if p:
                return clean_text(p.get_text(" ", strip=True))
    return None


def parse_nested_list(
    nested_list: Tag,
    rows,
    base_req_id: str,
    alpha_label: str,
    num_path: list[int],
    depth: int,
):
    li_tags = [c for c in nested_list.children if isinstance(c, Tag) and c.name == "li"]
    for idx, li in enumerate(li_tags, start=1):
        text = clean_text(li.get_text(" ", strip=True))
        full_path = [alpha_label] + num_path + [idx]
        ref_id = base_req_id + "." + ".".join(str(p) for p in full_path)
        add_row(rows, "x", depth, ref_id, "", text)

        for sub in li.find_all(["ol", "ul"], recursive=False):
            parse_nested_list(
                sub, rows, base_req_id, alpha_label, num_path + [idx], depth + 1
            )


def fetch_html(
    url: str, timeout: int = 30, progress_label: str = "Downloading page"
) -> str:
    with requests.get(
        url,
        stream=True,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; ITSP10.171-Scraper/1.0)",
            "Accept-Language": "fr-CA,fr;q=0.9,en;q=0.8",
        },
    ) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        chunks = []
        with tqdm(
            total=total if total > 0 else None,
            unit="B",
            unit_scale=True,
            desc=progress_label,
        ) as pbar:
            for chunk in resp.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                chunks.append(chunk)
                pbar.update(len(chunk))

        raw = b"".join(chunks)
        encoding = resp.encoding or resp.apparent_encoding or "utf-8"
    return raw.decode(encoding, errors="replace")


def iter_elements_until(start_tag: Tag, stop_predicate):
    for el in start_tag.next_elements:
        if isinstance(el, Tag) and stop_predicate(el):
            break
        yield el


def collect_text(elements) -> str:
    parts = []
    for el in elements:
        if isinstance(el, Tag) and el.name in ("p", "ul", "ol", "table"):
            text = clean_text(el.get_text(" ", strip=True))
            if text:
                parts.append(text)
    return clean_text(" ".join(parts))


def parse_requirement_detail(details_tag: Tag, rows):
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
            text = li_direct_text(li) or clean_text(li.get_text(" ", strip=True))
            add_row(rows, "x", 4, ref_a, "", text)
            used_alpha = True

            for sub in li.find_all(["ol", "ul"], recursive=False):
                parse_nested_list(sub, rows, req_id, alpha, [], 5)

    if not used_alpha:
        para = first_body_paragraph(details_tag)
        if para:
            add_row(rows, "x", 4, f"{req_id}.A", "", para)

    disc = extract_disc_text(details_tag)
    if disc:
        add_row(rows, "", 4, f"{req_id}.disc", "Discussion", disc)


def parse_requirements_from_html(html: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "lxml")
    rows = []

    for h2 in soup.find_all("h2", id=True):
        if not is_top_h2(h2):
            continue

        h2_txt = clean_text(h2.get_text(" ", strip=True))
        h2_match = TOP_H2_RE.match(h2_txt)
        top_id = h2_match.group(1)
        top_name = clean_text(h2_match.group(2))

        top_desc = collect_text(
            iter_elements_until(h2, lambda t: is_top_h2(t) or is_section_h3(t))
        )
        add_row(rows, "", 1, top_id, top_name, top_desc)

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
            sec_desc = collect_text(
                iter_elements_until(
                    h3,
                    lambda t: (
                        is_top_h2(t)
                        or is_section_h3(t)
                        or t.name == "details"
                        or is_requirement_h4(t)
                    ),
                )
            )
            add_row(rows, "", 2, sec_id, sec_name, sec_desc)

            for req_el in iter_elements_until(
                h3, lambda t: is_top_h2(t) or is_section_h3(t)
            ):
                if isinstance(req_el, Tag) and req_el.name == "details":
                    parse_requirement_detail(req_el, rows)

    return pd.DataFrame(
        rows, columns=["assessable", "depth", "ref_id", "name", "description"]
    )


def add_review_flag(df: pd.DataFrame) -> pd.DataFrame:
    def needs_review(desc):
        if pd.isna(desc):
            return ""
        return "x" if str(desc).rstrip().endswith(":") else ""

    df["review_flag"] = df["description"].apply(needs_review)
    return df


def build_excel_from_urls(
    source_url_fr: str = SOURCE_URL_FR,
    source_url_en: str = SOURCE_URL_EN,
    output_xlsx: str = OUTPUT_XLSX,
) -> str:
    html_fr = fetch_html(source_url_fr, progress_label="⤵️  Downloading [FR] page")
    html_en = fetch_html(source_url_en, progress_label="⤵️  Downloading [EN] page")

    df_fr = parse_requirements_from_html(html_fr)
    df_en = parse_requirements_from_html(html_en)[
        ["ref_id", "name", "description"]
    ].rename(columns={"name": "name[en]", "description": "description[en]"})

    df = df_fr.merge(df_en, on="ref_id", how="left")
    df = df[
        [
            "assessable",
            "depth",
            "ref_id",
            "name",
            "description",
            "name[en]",
            "description[en]",
        ]
    ]
    df = add_review_flag(df)

    with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="requirements")

    return output_xlsx


def main():
    output_path = build_excel_from_urls()
    print(f'✅ Export complete: "{output_path}"')


if __name__ == "__main__":
    main()
