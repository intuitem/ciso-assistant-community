"""Markdown fields in server-rendered exports.

Typst prints a string as literal text, so markdown reaches a template as a small
JSON tree that `core/typst/_markdown.typ` turns into content node by node. The
template never evaluates user text as markup: a `#` or `$` in a description
stays a character.

HTML exports use the same parser, whose `html: False` mode escapes raw HTML and
refuses `javascript:`-style links.
"""

from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

# Matches the frontend's MarkdownRenderer, whose `whitespace-pre-line` shows a
# single newline as a line break; raw HTML is text. markdown-it drops content
# nested past `maxNesting`, so it sits above MAX_DEPTH, where content is
# flattened instead.
_parser = MarkdownIt(
    "commonmark", {"html": False, "breaks": True, "maxNesting": 100}
).enable(["table", "strikethrough"])

_LINK_SCHEMES = ("http://", "https://", "mailto:")

# Typst bounds call depth; deeper input degrades to its text.
MAX_DEPTH = 16

_WRAPPERS = {"strong": "strong", "em": "em", "s": "s", "blockquote": "quote"}


def markdown_html(value) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    return _parser.render(value)


def markdown_tree(value):
    """`value` as a tree for the template's `md()`; empty values and the "-"
    placeholder pass through so templates' emptiness checks keep working."""
    if not isinstance(value, str) or value.strip() in ("", "-"):
        return value
    return {"t": "md", "c": _children(SyntaxTreeNode(_parser.parse(value)), 0)}


def _children(node, depth):
    return [converted for child in node.children for converted in _node(child, depth)]


def _text(node):
    if node.type in ("text", "code_inline", "fence", "code_block"):
        return node.content
    if node.type in ("softbreak", "hardbreak"):
        return " "
    return "".join(_text(child) for child in node.children)


def _node(node, depth):
    kind = node.type
    if kind == "text":
        return [node.content] if node.content else []
    if depth >= MAX_DEPTH:
        return [_text(node)]
    depth += 1

    if kind == "inline":
        return _children(node, depth)
    if kind == "paragraph":
        return [{"t": "span" if node.hidden else "p", "c": _children(node, depth)}]
    if kind == "heading":
        return [{"t": "h", "l": int(node.tag[1]), "c": _children(node, depth)}]
    if kind in _WRAPPERS:
        return [{"t": _WRAPPERS[kind], "c": _children(node, depth)}]
    if kind == "code_inline":
        return [{"t": "code", "v": node.content}]
    if kind in ("fence", "code_block"):
        return [{"t": "pre", "v": node.content.rstrip("\n")}]
    if kind in ("softbreak", "hardbreak"):
        return [{"t": "br"}]
    if kind == "hr":
        return [{"t": "hr"}]
    if kind == "link":
        href = str(node.attrs.get("href", ""))
        if href.lower().startswith(_LINK_SCHEMES):
            return [{"t": "a", "href": href, "c": _children(node, depth)}]
        return _children(node, depth)
    if kind == "image":
        # Remote images are never fetched at render time; keep the alt text.
        return _children(node, depth)
    if kind == "bullet_list":
        return [{"t": "ul", "c": [_item(item, depth) for item in node.children]}]
    if kind == "ordered_list":
        return [
            {
                "t": "ol",
                "start": int(node.attrs.get("start", 1)),
                "c": [_item(item, depth) for item in node.children],
            }
        ]
    if kind == "table":
        return [_table(node, depth)]
    return [_text(node)]


def _item(node, depth):
    return {"t": "li", "c": _children(node, depth)}


def _table(node, depth):
    rows = [
        [_children(cell, depth) for cell in row.children]
        for section in node.children
        for row in section.children
    ]
    header = bool(node.children) and node.children[0].type == "thead"
    return {
        "t": "table",
        "cols": max((len(row) for row in rows), default=1),
        "header": header,
        "rows": rows,
    }
