"""
Utility functions for PPTX processing.
"""

import os
import re
from typing import Any
from lxml import etree

from .constants import NAMESPACES, PLACEHOLDER_PATTERN


def register_namespaces():
    """Register all PPTX namespaces with lxml to preserve prefixes."""
    for prefix, uri in NAMESPACES.items():
        etree.register_namespace(prefix, uri)


def parse_xml(xml_path: str) -> etree._Element:
    """
    Parse an XML file and return the root element.

    Args:
        xml_path: Path to the XML file

    Returns:
        Root element of the parsed XML
    """
    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(xml_path, parser)
    return tree.getroot()


def write_xml(root: etree._Element, xml_path: str):
    """
    Write an XML element tree to a file.

    Args:
        root: Root element to write
        xml_path: Path to write the XML file
    """
    tree = etree.ElementTree(root)
    tree.write(
        xml_path,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )


def get_text_from_paragraph(p_element: etree._Element) -> str:
    """
    Extract all text content from a paragraph element.

    Args:
        p_element: A DrawingML paragraph element (a:p)

    Returns:
        Concatenated text from all text runs
    """
    texts = []
    for t_elem in p_element.iter(f"{{{NAMESPACES['a']}}}t"):
        if t_elem.text:
            texts.append(t_elem.text)
    return "".join(texts)


def get_text_from_shape(sp_element: etree._Element) -> str:
    """
    Extract all text content from a shape element.

    Args:
        sp_element: A PresentationML shape element (p:sp)

    Returns:
        Concatenated text from all paragraphs
    """
    texts = []
    for p_elem in sp_element.iter(f"{{{NAMESPACES['a']}}}p"):
        texts.append(get_text_from_paragraph(p_elem))
    return "\n".join(texts)


def find_placeholders(text: str) -> list[tuple[str, int, int]]:
    """
    Find all placeholders in a text string.

    Args:
        text: Text to search for placeholders

    Returns:
        List of tuples (placeholder_name, start_index, end_index)
    """
    placeholders = []
    for match in re.finditer(PLACEHOLDER_PATTERN, text):
        placeholders.append((match.group(1), match.start(), match.end()))
    return placeholders


def resolve_context_value(context: dict[str, Any], key: str) -> Any:
    """
    Resolve a potentially nested key from the context.

    Supports dot notation for nested access: 'user.name' -> context['user']['name']

    Args:
        context: The context dictionary
        key: The key to resolve (may contain dots for nested access)

    Returns:
        The resolved value or None if not found
    """
    parts = key.split(".")
    value = context

    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        elif hasattr(value, part):
            value = getattr(value, part)
        else:
            return None

        if value is None:
            return None

    return value


def get_shape_dimensions(sp_element: etree._Element) -> dict[str, int] | None:
    """
    Extract position and size from a shape element.

    Args:
        sp_element: A PresentationML shape element

    Returns:
        Dictionary with 'x', 'y', 'cx', 'cy' in EMUs, or None if not found
    """
    xfrm = sp_element.find(f".//{{{NAMESPACES['a']}}}xfrm")
    if xfrm is None:
        return None

    off = xfrm.find(f"{{{NAMESPACES['a']}}}off")
    ext = xfrm.find(f"{{{NAMESPACES['a']}}}ext")

    if off is None or ext is None:
        return None

    return {
        "x": int(off.get("x", 0)),
        "y": int(off.get("y", 0)),
        "cx": int(ext.get("cx", 0)),
        "cy": int(ext.get("cy", 0)),
    }


def get_next_shape_id(slide_root: etree._Element) -> int:
    """
    Find the next available shape ID in a slide.

    Args:
        slide_root: Root element of a slide XML

    Returns:
        Next available shape ID
    """
    max_id = 0
    for elem in slide_root.iter():
        id_attr = elem.get("id")
        if id_attr and id_attr.isdigit():
            max_id = max(max_id, int(id_attr))
    return max_id + 1


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal attacks.

    Args:
        filename: The filename to sanitize

    Returns:
        Sanitized filename
    """
    # Remove any path components
    filename = os.path.basename(filename)
    # Remove any potentially dangerous characters
    filename = re.sub(r"[^\w\-_\.]", "_", filename)
    return filename


def generate_unique_media_name(media_dir: str, extension: str) -> str:
    """
    Generate a unique filename for a media file.

    Args:
        media_dir: Path to the media directory
        extension: File extension (including dot)

    Returns:
        Unique filename
    """
    base_name = "image"
    counter = 1

    while True:
        filename = f"{base_name}{counter}{extension}"
        if not os.path.exists(os.path.join(media_dir, filename)):
            return filename
        counter += 1
