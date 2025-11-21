"""
    ANSSI Active Directory (AD) Security Assessment Checklist Extractor
    -------------------------------------------------------------------

    This script programmatically extracts the full content of the ANSSI "Active Directory
    Control Points" checklist (https://www.cert.ssi.gouv.fr/uploads/ad_checklist.html).
    It loads the dynamic React page via Playwright, switches to the English version if
    requested, expands all interactive sections, retrieves the HTML structure, and converts
    it into structured Markdown and JSON.

    The extractor reproduces:
        * Control point headers (Level, Title, Identifier)
        * Vulnerability descriptions and recommendations
        * Rich formatting (headings, paragraphs, spans, hyperlinks, code blocks)
        * Nested lists (ul/ol)
        * Formatted tables with checkbox rendering
        * Colorized spans extracted from runtime CSS
        * Special span logic (legend formatting, word+definition pairs)
        * Root-section metadata (intro + about control points)

    Results are exported as:
        * checklist.md              -> Complete Markdown export
        * checklist_markdown.json   -> Structured JSON preserving all fields

    /!\\ [IMPORTANT] Playwright installation /!\\ :
    ---------------------------------------------
    Playwright requires browser binaries to be installed **separately** from the Python package.
    To install everything correctly:

        pip install playwright
        playwright install          # downloads Chromium, Firefox, WebKit

    If running inside a virtual environment:
        python -m playwright install firefox

    Running the extractor:
    ----------------------
    Simply execute:

        python anssi_ad_web_scraper.py

    Playwright will launch Firefox in headless mode, simulate the language switch,
    collect the rendered HTML, and generate the Markdown/JSON output files.

    Notes for developers:
    ---------------------
    * The script relies heavily on Playwright's dynamic DOM evaluation and BeautifulSoup parsing.
    * CSS class names on the website are auto-generated; avoid targeting them directly.
    * Extraction logic is based on semantic structure (e.g., table headers, variant attributes),
    special cases (legend spans, code blocks), and stable DOM patterns rather than CSS classes.
    * If ANSSI updates the website, adjust the DOM selectors in extract_checklist().
    * The formatting layer is modular (render_inline, render_block, list rendering, code extraction)
    and can be extended easily if new HTML patterns appear.

"""



import json
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup, NavigableString, Tag


URL = "https://www.cert.ssi.gouv.fr/uploads/ad_checklist.html"

# Set this value to "True" in order to get the English version of the framework
FRAMEWORK_IN_ENGLISH = False



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


def smart_join(parts: list[str]) -> str:
    """
    Join inline text fragments while avoiding incorrect spaces around punctuation.

    Rules:
    - If the next fragment starts with punctuation like . , ; : ? ! ) ] } -> no space before it.
    - If the current result ends with an opening bracket like ( [ { -> no space before the next fragment.
    """
    if not parts:
        return ""

    result = parts[0]

    for part in parts[1:]:
        if not part:
            continue

        first_char = part[0]
        last_char = result[-1] if result else ""

        # Punctuation that should NOT be preceded by a space
        no_space_before = ".,;:?!)]}>"

        # Opening chars that should NOT be followed by a space
        no_space_after = "([{<"  # you can add more if needed

        if first_char in no_space_before or last_char in no_space_after:
            # glue directly
            result += part
        else:
            result += " " + part

    return result


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

    return smart_join(parts).strip()


def render_inline(tag: Tag) -> str:
    """
    Render an inline-level element (<b>, <a>, <span> with special classes, etc.)
    according to the rules.
    """
    name = tag.name.lower()
    
    # Ignore <button> elements completely
    if name == "button":
        return ""

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
            # if "href" is an anchor, add link of the website
            if href.startswith('#'):
                href = URL + href 
            
            return f"[{inner}]({href})"
        return inner

    # <span> with code-like classes -> `text`
    if name == "span":
        classes = tag.get("class") or []
        style = tag.get("style") or ""
        
        # Detect "code-like" spans
        is_code_like = (
            "hljs-built_in" in classes
            or has_class_prefix(tag, "sc-iBzDrC")
            or has_class_prefix(tag, "sc-jcwoBj")
        )


        # Extract background-color and color from inline style if present (will be applied for simple spans only)
        bg_color = None
        fg_color = None
        if style:
            for part in style.split(";"):
                part = part.strip()
                if not part:
                    continue
                lower = part.lower()
                if lower.startswith("background-color"):
                    _, value = part.split(":", 1)
                    bg_color = value.strip()
                elif lower.startswith("color"):
                    _, value = part.split(":", 1)
                    fg_color = value.strip()


        # ------------------------------------------------------
        # Case: WORD + DEFINITION spans (spanWord + spanDef)
        # (single definition item inside sc-hiKeQa)
        # ------------------------------------------------------
        """"
        # Structure:
        # <span class="sc-gXfWyg cUQUEo">
        #     [word-text or inline HTML]
        #     <span class="sc-hiKeQa PiEcp">[definition text]</span>
        # </span>
        #
        # Markdown result:
        # *word-text* (definition text)
        """
        if "sc-gXfWyg" in classes:

            # get all leaf spans (spans without nested spans)
            leaf_spans = []
            for s in tag.find_all("span", recursive=True):
                if s is tag:
                    continue
                if s.find("span"):
                    continue
                txt = s.get_text(strip=True)
                if txt:
                    leaf_spans.append(txt)

            # If exactly ONE leaf span -> it's a word+definition (NOT a legend)
            if len(leaf_spans) == 1:
                definition_text = leaf_spans[0]

                # extract word text (everything before the definition span)
                word_parts = []
                for child in tag.children:
                    # stop when reaching the span that contains the definition text
                    if isinstance(child, Tag) and definition_text in child.get_text():
                        break

                    if isinstance(child, NavigableString):
                        txt = child.strip()
                        if txt:
                            word_parts.append(txt)
                    elif isinstance(child, Tag):
                        rendered = render_inline(child)
                        if rendered:
                            word_parts.append(rendered)

                word_text = " ".join(word_parts).strip()

                if word_text and definition_text:
                    return f"*{word_text}* ({definition_text})"



        # Special case: phrase + list of spans -> "Phrase: item1, item2, ..."
        """
        # Example:
        # <span class="...">
        #   Legend
        #   <span>
        #       <span>Item 1</span>
        #       <span>Item 2</span>
        #       <span>Item 3</span>
        #   </span>
        # </span>
        """
        children = list(tag.children)
        if children and isinstance(children[0], NavigableString):
            phrase = children[0].strip()

            # Collect only leaf <span> descendants (those that do not contain other spans)
            leaf_spans = []
            for s in tag.find_all("span", recursive=True):
                if s is tag:
                    continue  # skip the wrapper span itself
                if s.find("span"):
                    continue  # not a leaf, contains nested spans
                txt = s.get_text(strip=True)
                if txt:
                    leaf_spans.append(txt)

            if phrase and leaf_spans:
                # Example: "Legend: Item 1, Item 2, Item 3"
                return f"{phrase}: {', '.join(leaf_spans)}"


        ### > Generic span fallback: inline content, possibly code-like, possibly colored
        inner = render_inline_children(tag)
        if not inner:
            return ""

        content = inner

        # Apply inline code formatting if this is a "code-like" span
        if is_code_like:
            content = f"`{content}`"

        # Apply style if we have background and/or text color
        if bg_color or fg_color:
            style_bits = []
            if bg_color:
                style_bits.append(f"background-color:{bg_color}")
            if fg_color:
                style_bits.append(f"color:{fg_color}")
            style_attr = ";".join(style_bits)
            
            if "`" in content:
                return f"<code style=\"{style_attr}\">{content.replace("`", "")}</code>"
            else:
                return f"<span style=\"{style_attr}\">{content}</span>"

        return content
        ### > [END] Generic span fallback:


    # Anything else inline-like -> render its children
    return render_inline_children(tag)


def render_block(node: Tag) -> str:
    """
    Render a block-level node (p, h1, h2, ul, ol, table, div[variant=code], etc.)
    to Markdown, including trailing newlines.
    """
    name = node.name.lower()
    
    # Ignore <button> and its entire subtree
    if name == "button":
        return ""

    # Headings
    if name == "h1":
        inner = render_inline_children(node)
        if not inner:
            return ""
        
        # Capitalize first letter only
        inner = inner[0].upper() + inner[1:]
        return f"# {inner}\n\n"

    if name == "h2":
        inner = render_inline_children(node)
        if not inner:
            return ""
        
        # Capitalize first letter only
        inner = inner[0].upper() + inner[1:]
        return f"## {inner}\n\n"

    # Paragraph
    if name == "p":
        inner = render_inline_children(node)
        if not inner:
            return ""
        return f"{inner}\n\n"

    # Ordered list <ol>
    if name == "ol":
        return render_list(node, level=0, ordered=True)

    # Unordered list <ul>
    if name == "ul":
        return render_list(node, level=0, ordered=False)

    # Tables -> Markdown table with empty header
    if name == "table":
        
        table_body = node.find("tbody")
        
        rows = table_body.find_all("tr", recursive=False)
        if not rows:
            return ""
        
        # Remove 1st row because it contains a button
        rows = rows[1:]

        # Determine column count from 2nd row
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
            contents = [render_table_cell(td) for td in cells]
            body_lines.append("| " + " | ".join(contents) + " |")

        table_md = header + separator + "\n".join(body_lines) + "\n\n"
        return table_md

    # <div variant="code"> -> ```code```
    if name == "div" and node.get("variant") == "code":
        code_text = extract_code_from_variant_div(node)
        if not code_text:
            return ""
        return f"```powershell\n{code_text}\n```\n\n"

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


def render_list(node: Tag, level: int, ordered: bool) -> str:
    """
    Render a <ul> or <ol> node (possibly nested) to Markdown.
    - level: nesting level (0 = root list)
    - ordered: True for <ol>, False for <ul>
    """
    lines = []
    idx = 1
    indent = "  " * level  # two spaces per nesting level

    for child in node.children:
        if isinstance(child, NavigableString):
            continue
        if not isinstance(child, Tag):
            continue

        # List item
        if child.name.lower() == "li":
            text = render_inline_children(child).strip()
            if text:
                if ordered:
                    # Ordered list: "X. "
                    prefix = f"{idx}. "
                    idx += 1
                else:
                    # Unordered list: "* "
                    prefix = "* "
                lines.append(f"{indent}{prefix}{text}")

            # Handle nested lists inside this <li> (proper HTML)
            for sub in child.children:
                if isinstance(sub, Tag) and sub.name.lower() in ("ul", "ol"):
                    nested_md = render_list(
                        sub,
                        level + 1,
                        ordered=(sub.name.lower() == "ol"),
                    )
                    if nested_md:
                        nested_lines = nested_md.rstrip("\n").split("\n")
                        lines.extend(nested_lines)

        # Nested lists as siblings of <li> (messy HTML case)
        elif child.name.lower() in ("ul", "ol"):
            nested_md = render_list(
                child,
                level + 1,
                ordered=(child.name.lower() == "ol"),
            )
            if nested_md:
                nested_lines = nested_md.rstrip("\n").split("\n")
                lines.extend(nested_lines)

    if not lines:
        return ""

    return "\n".join(lines) + "\n\n"


def render_table_cell(td: Tag) -> str:
    """
    Render a <td>/<th> cell to Markdown content.
    If it contains checkbox inputs, render them as HTML <input type="checkbox"... />
    followed by the label text.
    """
    # Find checkbox inputs inside the cell
    checkbox_inputs = td.find_all("input", attrs={"type": "checkbox"}, recursive=True)

    if checkbox_inputs:
        parts = []

        for inp in checkbox_inputs:
            attrs = ['type="checkbox"']
            if inp.has_attr("disabled"):
                attrs.append("disabled")
            if inp.has_attr("checked"):
                attrs.append("checked")

            checkbox_html = f"<input {" ".join(attrs)} />"
            parts.append(checkbox_html)

        # Try to get associated label text(s)
        label_texts = []
        for lbl in td.find_all("label", recursive=True):
            txt = render_inline_children(lbl).strip()
            if txt:
                label_texts.append(txt)

        if label_texts:
            parts.append(" ".join(label_texts))

        return " ".join(parts).strip()

    # Fallback: normal cell content
    return render_inline_children(td)


def extract_code_from_variant_div(node: Tag) -> str:
    """
    Extract code text from a <div variant="code"> block.
    - Preserve line breaks only where there are <br> tags.
    - Ignore markup (span, classes, etc.).
    """
    # On some blocks, the actual code is inside an inner <div>, like in your example.
    inner = node.find("div") or node

    lines = []
    buffer = []

    for element in inner.descendants:
        if isinstance(element, NavigableString):
            # Keep raw text, including spaces
            buffer.append(str(element))
            
        elif isinstance(element, Tag):
            
            name = element.name.lower()
            
            if name == "br":
                # Flush current buffer as a line
                line = "".join(buffer)
                # Normalize non-breaking spaces and strip right side
                line = line.replace("\xa0", " ").rstrip()
                lines.append(line)
                buffer = []

    # Flush last line if any remaining text
    if buffer:
        line = "".join(buffer)
        line = line.replace("\xa0", " ").rstrip()
        
        if line:
            lines.append(line)

    # Remove leading/trailing empty lines, just in case
    while lines and not lines[0].strip():
        lines.pop(0)
        
    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(lines)


def format_root_secondary_html(html: str) -> str:
    """
    Format a root-level <div variant="secondary"> fragment (intro / about_ctrl_points)
    using the same Markdown rendering logic as the rest.
    """
    soup = BeautifulSoup(html, "html.parser")
    root = soup

    parts = []
    for child in root.children:
        if isinstance(child, Tag):
            parts.append(render_block(child))

    return "".join(parts).strip()


def format_description_html(html: str) -> str:
    """
    Apply description-specific rules:
    - divA contains h1, p, spans, etc.
    - div[variant="secondary"] moved to end (order preserved)
    - div[variant="info"] moved last (order preserved)
    """
    soup = BeautifulSoup(html, "html.parser")
    divA = soup  # important: we work on the whole fragment, not soup.find("div")

    main_parts = []
    secondary_divs = []
    info_divs = []

    for child in divA.children:
        if not isinstance(child, Tag):
            continue  # we ignore raw text in divA

        if child.name.lower() == "div":
            variant = child.get("variant")

            if variant == "secondary":
                # store rendered block (NOT the tag itself)
                secondary_divs.append(render_block(child))
                continue

            if variant == "info":
                # store rendered block
                info_divs.append(render_block(child))
                continue

        # Normal element (p, h1, ul, table, or even nested div)
        main_parts.append(render_block(child))

    return (
        "".join(main_parts)
        + "".join(secondary_divs)
        + "".join(info_divs)
    ).strip()



def format_recommendation_html(html: str) -> str:
    """
    Apply recommendation-specific rules:
    - normal content first
    - then ALL extra blocks (info/warning) in exact HTML order
    """
    soup = BeautifulSoup(html, "html.parser")
    divB = soup  # important: we work on the whole fragment, not soup.find("div")

    main_parts = []
    extra_divs = []  # preserve appearance order

    for child in divB.children:
        if not isinstance(child, Tag):
            continue  # ignore raw text

        if child.name.lower() == "div":
            variant = child.get("variant")

            if variant in ("info", "warning"):
                # store rendered block immediately (order preserved)
                extra_divs.append(render_block(child))
                continue

        # normal item (p, h1, table, …)
        main_parts.append(render_block(child))

    return (
        "".join(main_parts)
        + "".join(extra_divs)
    ).strip()




# ---------------- Checklist extraction with Playwright ---------------- #

def extract_checklist(framework_in_english : bool = False):
    results = []

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()

        page.goto(URL, wait_until="load")

        # Wait until at least one header TR is mounted
        page.wait_for_selector("div#root table tbody tr td:nth-child(2)")
        
        use_english = False
        
        if framework_in_english is not None:
            use_english = framework_in_english
        else:
            use_english = FRAMEWORK_IN_ENGLISH
            
        if use_english:
            print("> ⌛ Switching page to English...")
            # Find the button whose inner text contains "EN"
            en_button = page.locator("nav button:has-text('EN')")

            # If the button exists, click it
            if en_button.count() > 0:
                en_button.first.click()

                # Wait for the language to switch (e.g. title changes)
                page.wait_for_timeout(1000)  # small delay to allow refresh
                
                print("> ✅ Page switched to English !")
            else:
                print("> ⚠️ English switch button not found")
        else:
            print("> ✅ Using default language for page (French)")
        
        
        # > Specific code for span in order to give them colors in the Markdown 
        # Inject computed background-color as inline style on level spans
        page.evaluate(
            """
            () => {
                // Select spans that get color from CSS based on "level" and class families
                const spans = document.querySelectorAll(
                    'span[level].sc-jJMFAr, span[level].sc-bBjSGg, span.sc-cOifbb, span[level].sc-ArjuK'
                );

                // Take "color" and "background-color" of spans to add those colors in Markdown 
                spans.forEach(span => {
                    const cs = window.getComputedStyle(span);
                    if (cs && cs.backgroundColor && !span.style.backgroundColor) {
                        span.style.backgroundColor = cs.backgroundColor;
                    }
                    if (cs.color && !span.style.color) {
                        span.style.color = cs.color;
                    }
                });
            }
            """
        )
        
        
        # --- Root-level secondary divs: intro and about_ctrl_points ---
        root_intro_md = ""
        root_about_md = ""
        root_elements = []

        # Find all secondary variant divs inside #root (global ones are first)
        root_secondary_divs = page.query_selector_all("div#root div[variant='secondary']")

        if len(root_secondary_divs) >= 1:
            intro_html = root_secondary_divs[0].inner_html()
            root_intro_md = format_root_secondary_html(intro_html)
            if root_intro_md:
                root_elements.append(
                    {
                        "root_element": "intro",
                        "content_markdown": root_intro_md,
                    }
                )

        if len(root_secondary_divs) >= 2:
            about_html = root_secondary_divs[1].inner_html()
            root_about_md = format_root_secondary_html(about_html)
            if root_about_md:
                root_elements.append(
                    {
                        "root_element": "about_ctrl_points",
                        "content_markdown": root_about_md,
                    }
                )


        # --- Table with all vulnerabilities ---
        
        # Retrieve all TR elements
        rows = page.query_selector_all("div#root > div > table > tbody > tr")

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


    # Form complete website
    complete_website = {
        "root_elements": root_elements,
        "checklist": results,
    }

    return complete_website


# ---------------- Main ---------------- #

# A 2nd "framework_in_english" has been added to let external calls to select a language (the default one will be used if no boolean given)
def main(framework_in_english: bool = False, files_suffix: str = None):
    
    print(f"⌛ Extracting Framework from website \"{URL}\"...")
    
    data = extract_checklist(framework_in_english)
    
    print(f"✅ Extraction finished!\n")
    
    root_elements = data.get("root_elements", [])
    checklist = data.get("checklist", [])
    
    print(f"ℹ️  Elements found in checklist: {len(checklist)} ")
    
    markdown_filename = f"checklist{'_' + files_suffix if files_suffix else ""}.md"
    json_filename = f"checklist_markdown{'_' + files_suffix if files_suffix else ""}.json"

    # --- Save everything into a single Markdown file ---
    with open(markdown_filename, "w", encoding="utf-8") as f:

        # 1) Root-level elements (intro + about_ctrl_points)
        for root in root_elements:
            f.write(f"# ROOT: {root['root_element']}\n\n")
            f.write(root["content_markdown"])
            f.write("\n\n---\n\n")

        # 2) Checklist items
        for entry in checklist:
            f.write(f"# {entry['identifier']} - {entry['title']}\n\n")
            f.write(f"**Level:** {entry['level']}\n\n")

            f.write("## Description\n\n")
            f.write(entry["description_markdown"])
            f.write("\n\n")

            f.write("## Recommendation\n\n")
            f.write(entry["recommendation_markdown"])
            f.write("\n\n---\n\n")

    print(f"✅ Markdown file saved: \"{markdown_filename}\"")

    # --- Save JSON ---
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"✅ JSON file saved: \"{json_filename}\"")



if __name__ == "__main__":
    main()