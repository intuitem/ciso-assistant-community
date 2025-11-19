import json
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup, NavigableString, Tag

URL = "https://www.cert.ssi.gouv.fr/uploads/ad_checklist.html"


# ---------------- Markdown formatting helpers ---------------- #

def text_of(node) -> str:
    """Get plain text of a node, stripped."""
    if isinstance(node, NavigableString):
        return str(node).strip()
    if isinstance(node, Tag):
        return node.get_text(strip=True)
    return ""


def has_class_prefix(tag: Tag, prefix: str) -> bool:
    classes = tag.get("class") or []
    return any(c.startswith(prefix) for c in classes)


def is_inline_tag(tag_name: str) -> bool:
    """Tags considered inline for spacing logic."""
    return tag_name in {
        "b", "strong", "a", "span", "code", "em", "i",
    }


def render_inline_children(parent: Tag) -> str:
    """
    Render children of a node as inline content:
    - merge pieces with single spaces
    - avoid extra spaces
    """
    parts = []

    for child in parent.children:
        if isinstance(child, NavigableString):
            txt = str(child).strip()
            if txt:
                parts.append(txt)
        elif isinstance(child, Tag):
            rendered = render_inline(child)
            if rendered:
                parts.append(rendered.strip())

    return " ".join(parts).strip()


def render_inline(tag: Tag) -> str:
    """
    Render an inline-level element (<b>, <a>, <span> with special classes, etc.)
    according to the rules.
    """
    name = tag.name.lower()

    # <b> or <strong> -> **text**
    if name in ("b", "strong"):
        inner = render_inline_children(tag)
        if not inner:
            return ""
        return f"**{inner}**"

    # <a> -> [text](href)
    if name == "a":
        href = (tag.get("href") or "").strip()
        inner = render_inline_children(tag)
        if not inner:
            return ""
        if href:
            return f"[{inner}]({href})"
        return inner

    # <span> with code-like classes -> `text`
    if name == "span":
        classes = tag.get("class") or []
        style = tag.get("style") or ""

        # class="hljs-built_in" OR classes starting with "sc-iBzDrC hDbjJb"
        if "hljs-built_in" in classes or has_class_prefix(tag, "sc-iBzDrC hDbjJb"):
            inner = render_inline_children(tag)
            if not inner:
                return ""
            return f"`{inner}`"

        # span with explicit background-color style -> <font color=COLOR>TEXT</font>
        if "background-color" in style:
            # very simple parsing
            color = None
            for part in style.split(";"):
                part = part.strip()
                if part.lower().startswith("background-color"):
                    _, value = part.split(":", 1)
                    color = value.strip()
                    break
            inner = render_inline_children(tag)
            if not inner:
                return ""
            if color:
                return f"<font color={color}>{inner}</font>"
            return inner

        # Special case: phrase + list of spans -> "Phrase: item1, item2, ..."
        children = list(tag.children)
        if children and isinstance(children[0], NavigableString):
            phrase = str(children[0]).strip()
            span_items = [
                text_of(c)
                for c in children[1:]
                if isinstance(c, Tag) and c.name.lower() == "span"
            ]
            if phrase and span_items:
                return f"{phrase}: {', '.join(span_items)}"

        # Generic span: just render its inline content
        return render_inline_children(tag)

    # Anything else inline-like -> render its children
    return render_inline_children(tag)


def render_block(node: Tag) -> str:
    """
    Render a block-level node (p, h1, h2, ul, ol, table, div[variant=code], etc.)
    to Markdown, including trailing newlines.
    """
    name = node.name.lower()

    # Headings
    if name == "h1":
        inner = render_inline_children(node)
        if not inner:
            return ""
        return f"# {inner}\n\n"

    if name == "h2":
        inner = render_inline_children(node)
        if not inner:
            return ""
        return f"## {inner}\n\n"

    # Paragraph
    if name == "p":
        inner = render_inline_children(node)
        if not inner:
            return ""
        return f"{inner}\n\n"

    # Ordered list <ol>
    if name == "ol":
        lines = []
        idx = 1
        for li in node.find_all("li", recursive=False):
            txt = render_inline_children(li)
            if txt:
                # "X " prefix (no dot)
                lines.append(f"{idx} {txt}")
                idx += 1
        if not lines:
            return ""
        return "\n".join(lines) + "\n\n"

    # Unordered list <ul>
    if name == "ul":
        lines = []
        for li in node.find_all("li", recursive=False):
            txt = render_inline_children(li)
            if txt:
                lines.append(f"* {txt}")
        if not lines:
            return ""
        return "\n".join(lines) + "\n\n"

    # Tables -> Markdown table with empty header
    if name == "table":
        rows = node.find_all("tr", recursive=False)
        if not rows:
            return ""

        # Determine column count from first row
        first_cells = rows[0].find_all(["td", "th"], recursive=False)
        if not first_cells:
            return ""

        col_count = len(first_cells)
        header = "| " + " | ".join([""] * col_count) + " |\n"
        separator = "| " + " | ".join(["---"] * col_count) + " |\n"

        body_lines = []
        for tr in rows:
            cells = tr.find_all(["td", "th"], recursive=False)
            if not cells:
                continue
            contents = [render_inline_children(td) for td in cells]
            body_lines.append("| " + " | ".join(contents) + " |")

        table_md = header + separator + "\n".join(body_lines) + "\n\n"
        return table_md

    # <div variant="code"> -> ```code```
    if name == "div" and node.get("variant") == "code":
        code_text = node.get_text("\n", strip=True)
        if not code_text:
            return ""
        return f"```\n{code_text}\n```\n\n"

    # Generic <div> or other block: render children as a sequence of blocks
    parts = []
    for child in node.children:
        if isinstance(child, NavigableString):
            txt = str(child).strip()
            if txt:
                parts.append(txt + "\n\n")
        elif isinstance(child, Tag):
            # block vs inline: if inline tag, render as a paragraph
            if is_inline_tag(child.name.lower()):
                inline_txt = render_inline(child)
                if inline_txt:
                    parts.append(inline_txt + "\n\n")
            else:
                parts.append(render_block(child))

    return "".join(parts)


def format_description_html(html: str) -> str:
    """
    Apply description-specific rules:
    - divA contains h1, p, spans, etc.
    - div[variant="secondary"] processed at the end, before div[variant="info"]
    - div[variant="info"] processed last
    """
    soup = BeautifulSoup(html, "html.parser")
    divA = soup.find("div") or soup

    main_parts = []
    secondary_divs = []
    info_divs = []

    for child in divA.children:
        if isinstance(child, NavigableString):
            txt = str(child).strip()
            if txt:
                main_parts.append(txt + "\n\n")
        elif isinstance(child, Tag):
            if child.name.lower() == "div":
                variant = child.get("variant")
                if variant == "secondary":
                    secondary_divs.append(child)
                    continue
                if variant == "info":
                    info_divs.append(child)
                    continue

            # normal block in description
            main_parts.append(render_block(child))

    # Process secondary blocks (divSec) first
    for sec in secondary_divs:
        main_parts.append(render_block(sec))

    # Then info blocks (divInfo)
    for info in info_divs:
        main_parts.append(render_block(info))

    return "".join(main_parts).strip()


def format_recommendation_html(html: str) -> str:
    """
    Apply recommendation-specific rules:
    - divB contains h1, p, etc.
    - divExtras: div[variant="info"] and/or div[variant="warning"]
      processed at the end, in order of appearance.
    """
    soup = BeautifulSoup(html, "html.parser")
    divB = soup.find("div") or soup

    main_parts = []
    extra_divs = []  # info / warning, in appearance order

    for child in divB.children:
        if isinstance(child, NavigableString):
            txt = str(child).strip()
            if txt:
                main_parts.append(txt + "\n\n")
        elif isinstance(child, Tag):
            if child.name.lower() == "div":
                variant = child.get("variant")
                if variant in ("info", "warning"):
                    extra_divs.append(child)
                    continue

            main_parts.append(render_block(child))

    # Extra blocks at the end, in original order
    for extra in extra_divs:
        main_parts.append(render_block(extra))

    return "".join(main_parts).strip()


# ---------------- Checklist extraction with Playwright ---------------- #

def extract_checklist():
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(URL, wait_until="load")

        # Wait until at least one header TR is mounted
        page.wait_for_selector("div#root table tbody tr td:nth-child(2)")

        # Retrieve all TR elements
        rows = page.query_selector_all("div#root table tbody tr")

        i = 0
        while i < len(rows):
            row = rows[i]
            cells = row.query_selector_all("td")

            # A header row: >= 3 visible cells
            if len(cells) >= 3:
                level = cells[0].inner_text().strip()
                title = cells[1].inner_text().strip()
                identifier = cells[-1].inner_text().strip()

                description_md = ""
                recommendation_md = ""

                # Description row: next TR, hidden, contains divA
                if i + 1 < len(rows):
                    desc_row = rows[i + 1]
                    if desc_row.get_attribute("hidden") is not None:
                        desc_div = desc_row.query_selector("div")
                        if desc_div:
                            desc_html = desc_div.inner_html()
                            description_md = format_description_html(desc_html)

                # Recommendation row: second hidden TR, contains divB
                if i + 2 < len(rows):
                    reco_row = rows[i + 2]
                    if reco_row.get_attribute("hidden") is not None:
                        reco_div = reco_row.query_selector("div")
                        if reco_div:
                            reco_html = reco_div.inner_html()
                            recommendation_md = format_recommendation_html(reco_html)

                results.append(
                    {
                        "level": level,
                        "title": title,
                        "identifier": identifier,
                        "description_markdown": description_md,
                        "recommendation_markdown": recommendation_md,
                    }
                )

                i += 3  # Skip the two hidden rows linked to this header
            else:
                i += 1

        browser.close()

    return results


# ---------------- Main ---------------- #

if __name__ == "__main__":
    data = extract_checklist()
    
    # --- Save everything into a single Markdown file ---
    with open("checklist.md", "w", encoding="utf-8") as f:
        for entry in data:
            f.write(f"# {entry['identifier']} - {entry['title']}\n\n")
            f.write(f"**Level:** {entry['level']}\n\n")

            f.write("## Description\n\n")
            f.write(entry["description_markdown"])
            f.write("\n\n")

            f.write("## Recommendation\n\n")
            f.write(entry["recommendation_markdown"])
            f.write("\n\n---\n\n")

    print("✓ Markdown file saved: checklist.md")



    print(f"Number of checklist items found: {len(data)}\n")
    for entry in data[:3]:  # show first few for sanity check
        print("Level:", entry["level"])
        print("Title:", entry["title"])
        print("ID:", entry["identifier"])
        print("\n--- Description (MD) ---\n")
        print(entry["description_markdown"][:600], "...\n")
        print("\n--- Recommendation (MD) ---\n")
        print(entry["recommendation_markdown"][:600], "...\n")
        print("=" * 80)

    # --- Save JSON ---
    with open("checklist_markdown.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print("\n✓ JSON file saved: checklist_markdown.json")
