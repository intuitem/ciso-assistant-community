from urllib.parse import urlsplit

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore

SAFE_LINK_SCHEMES = ["http", "https"]


def _is_safe_href(href: str) -> bool:
    try:
        return urlsplit(href).scheme in SAFE_LINK_SCHEMES
    except ValueError:
        return False


def _neutralise_links_and_images(state: StateCore) -> None:
    """Keep http(s) links, turn other links into plain spans and images into
    their alt text."""
    for block in state.tokens:
        is_unsafe_link = False
        for token in block.children or []:
            if token.type == "image":
                alt = state.md.renderer.renderInlineAsText(
                    token.children or [], state.md.options, state.env
                )
                token.type, token.tag, token.attrs = "text", "", {}
                token.children, token.content = None, alt
            elif token.type == "link_open":
                is_unsafe_link = not _is_safe_href(str(token.attrGet("href") or ""))
                if is_unsafe_link:
                    token.tag, token.attrs = "span", {}
                else:
                    token.attrSet("rel", "noopener noreferrer")
                    token.attrSet("target", "_blank")
            elif token.type == "link_close" and is_unsafe_link:
                token.tag = "span"
                is_unsafe_link = False


_MARKDOWN = MarkdownIt("commonmark", {"html": False, "breaks": True}).enable(
    ["table", "strikethrough"]
)
# Every link is parsed so `_neutralise_links_and_images` decides its fate:
# markdown-it's own filter would leave rejected links as raw Markdown text.
_MARKDOWN.validateLink = lambda url: True
_MARKDOWN.core.ruler.push("neutralise_links_and_images", _neutralise_links_and_images)


def render_safe_markdown(text: str | None) -> str:
    """Return `text` rendered from Markdown to HTML, or an empty string.

    Used for documents opened outside the app: raw HTML is escaped rather than
    passed through, links keep only http(s) targets, and images are replaced by
    their alt text, since a remote image would call a third-party server every
    time the document is opened.
    """
    if not text:
        return ""
    return _MARKDOWN.render(text)
