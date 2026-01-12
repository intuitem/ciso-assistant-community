"""
Image placeholder replacer for PPTX templates.

Handles {{image:variable}} style placeholders, replacing text boxes with images.
"""

import os
import re
import shutil
from typing import Any
from lxml import etree

from ..constants import (
    NAMESPACES,
    IMAGE_PLACEHOLDER_PATTERN,
    IMAGE_CONTENT_TYPES,
    REL_TYPE_IMAGE,
    MEDIA_DIR,
)
from ..exceptions import ImageError, MissingContextError
from ..utils import (
    resolve_context_value,
    get_shape_dimensions,
    get_next_shape_id,
    sanitize_filename,
    generate_unique_media_name,
)


class ImageReplacer:
    """
    Replaces image placeholders in PPTX XML with actual images.

    The placeholder text box is converted to a picture element, maintaining
    the original position and dimensions.
    """

    def __init__(
        self,
        context: dict[str, Any],
        working_dir: str,
        strict: bool = False,
    ):
        """
        Initialize the image replacer.

        Args:
            context: Dictionary of values (image paths) to substitute
            working_dir: Path to the extracted PPTX working directory
            strict: If True, raise error on missing images
        """
        self.context = context
        self.working_dir = working_dir
        self.strict = strict
        self.a_ns = f"{{{NAMESPACES['a']}}}"
        self.p_ns = f"{{{NAMESPACES['p']}}}"
        self.r_ns = f"{{{NAMESPACES['r']}}}"
        # Track images added
        self.images_added: list[dict] = []

    def replace_in_slide(
        self,
        slide_root: etree._Element,
        slide_path: str,
        slide_num: int = None,
    ) -> etree._Element:
        """
        Replace all image placeholders in a slide.

        Args:
            slide_root: Root element of a slide XML
            slide_path: Path to the slide XML file
            slide_num: Slide number for error reporting

        Returns:
            The modified slide root
        """
        # Find all shapes with image placeholders
        shapes_to_replace = []

        for sp_elem in slide_root.iter(f"{self.p_ns}sp"):
            # Get all text from this shape
            shape_text = self._get_shape_text(sp_elem)

            # Check for image placeholder
            match = re.search(IMAGE_PLACEHOLDER_PATTERN, shape_text)
            if match:
                placeholder_name = match.group(1)
                shapes_to_replace.append((sp_elem, placeholder_name, match.group(0)))

        # Replace shapes with images
        for sp_elem, placeholder_name, full_placeholder in shapes_to_replace:
            self._replace_shape_with_image(
                slide_root,
                sp_elem,
                placeholder_name,
                full_placeholder,
                slide_path,
                slide_num,
            )

        return slide_root

    def _get_shape_text(self, sp_element: etree._Element) -> str:
        """Extract all text from a shape element."""
        texts = []
        for t_elem in sp_element.iter(f"{self.a_ns}t"):
            if t_elem.text:
                texts.append(t_elem.text)
        return "".join(texts)

    def _replace_shape_with_image(
        self,
        slide_root: etree._Element,
        sp_element: etree._Element,
        placeholder_name: str,
        full_placeholder: str,
        slide_path: str,
        slide_num: int = None,
    ) -> None:
        """
        Replace a text shape with an image.

        Args:
            slide_root: Root element of the slide
            sp_element: The shape element to replace
            placeholder_name: Name of the placeholder (without image: prefix)
            full_placeholder: Full placeholder text including {{image:}}
            slide_path: Path to the slide XML file
            slide_num: Slide number for error reporting
        """
        # Get image path from context
        image_path = resolve_context_value(self.context, placeholder_name)

        if image_path is None or not image_path:
            if self.strict:
                raise MissingContextError(f"image:{placeholder_name}", slide_num)
            # Remove the shape if no image provided in non-strict mode
            parent = sp_element.getparent()
            if parent is not None:
                parent.remove(sp_element)
            return

        # Validate image file exists
        if not os.path.isfile(image_path):
            raise ImageError(
                f"Image file not found",
                image_path=image_path,
                placeholder=placeholder_name,
            )

        # Get file extension and validate
        _, ext = os.path.splitext(image_path)
        ext = ext.lower()

        if ext not in IMAGE_CONTENT_TYPES:
            raise ImageError(
                f"Unsupported image format '{ext}'",
                image_path=image_path,
                placeholder=placeholder_name,
            )

        # Get shape dimensions
        dimensions = get_shape_dimensions(sp_element)
        if dimensions is None:
            raise ImageError(
                "Could not determine shape dimensions",
                placeholder=placeholder_name,
            )

        # Copy image to media directory
        media_dir = os.path.join(self.working_dir, MEDIA_DIR)
        os.makedirs(media_dir, exist_ok=True)

        media_filename = generate_unique_media_name(media_dir, ext)
        media_path = os.path.join(media_dir, media_filename)
        shutil.copy2(image_path, media_path)

        # Add relationship
        rel_id = self._add_image_relationship(slide_path, media_filename)

        # Update content types if needed
        self._ensure_content_type(ext)

        # Create picture element
        pic_element = self._create_picture_element(
            dimensions,
            rel_id,
            get_next_shape_id(slide_root),
            placeholder_name,
        )

        # Replace shape with picture
        parent = sp_element.getparent()
        if parent is not None:
            index = list(parent).index(sp_element)
            parent.remove(sp_element)
            parent.insert(index, pic_element)

        # Track the replacement
        self.images_added.append(
            {
                "placeholder": placeholder_name,
                "source_path": image_path,
                "media_path": media_path,
                "slide": slide_num,
            }
        )

    def _add_image_relationship(self, slide_path: str, media_filename: str) -> str:
        """
        Add an image relationship to the slide's .rels file.

        Args:
            slide_path: Path to the slide XML file
            media_filename: Name of the media file

        Returns:
            The relationship ID (rId)
        """
        # Construct rels file path
        slide_dir = os.path.dirname(slide_path)
        slide_name = os.path.basename(slide_path)
        rels_dir = os.path.join(slide_dir, "_rels")
        rels_path = os.path.join(rels_dir, f"{slide_name}.rels")

        # Ensure rels directory exists
        os.makedirs(rels_dir, exist_ok=True)

        # Parse or create rels file
        rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"

        if os.path.exists(rels_path):
            tree = etree.parse(rels_path)
            root = tree.getroot()
        else:
            root = etree.Element(f"{{{rel_ns}}}Relationships", nsmap={None: rel_ns})

        # Find next available rId
        existing_ids = []
        for rel in root.findall(f"{{{rel_ns}}}Relationship"):
            rel_id = rel.get("Id", "")
            if rel_id.startswith("rId"):
                try:
                    existing_ids.append(int(rel_id[3:]))
                except ValueError:
                    pass

        next_id = max(existing_ids, default=0) + 1
        new_rel_id = f"rId{next_id}"

        # Add relationship
        etree.SubElement(
            root,
            f"{{{rel_ns}}}Relationship",
            {
                "Id": new_rel_id,
                "Type": REL_TYPE_IMAGE,
                "Target": f"../media/{media_filename}",
            },
        )

        # Write rels file
        tree = etree.ElementTree(root)
        tree.write(rels_path, xml_declaration=True, encoding="UTF-8", standalone=True)

        return new_rel_id

    def _ensure_content_type(self, extension: str) -> None:
        """
        Ensure the content type for an image extension is registered.

        Args:
            extension: File extension (including dot)
        """
        content_types_path = os.path.join(self.working_dir, "[Content_Types].xml")

        if not os.path.exists(content_types_path):
            return

        tree = etree.parse(content_types_path)
        root = tree.getroot()
        ct_ns = "http://schemas.openxmlformats.org/package/2006/content-types"

        # Check if extension already registered
        ext_without_dot = extension.lstrip(".")

        for default in root.findall(f"{{{ct_ns}}}Default"):
            if default.get("Extension", "").lower() == ext_without_dot.lower():
                return  # Already registered

        # Add the content type
        content_type = IMAGE_CONTENT_TYPES.get(extension, "application/octet-stream")
        etree.SubElement(
            root,
            f"{{{ct_ns}}}Default",
            {"Extension": ext_without_dot, "ContentType": content_type},
        )

        tree.write(
            content_types_path, xml_declaration=True, encoding="UTF-8", standalone=True
        )

    def _create_picture_element(
        self,
        dimensions: dict[str, int],
        rel_id: str,
        shape_id: int,
        name: str,
    ) -> etree._Element:
        """
        Create a picture element (p:pic) for the slide.

        Args:
            dimensions: Dictionary with x, y, cx, cy in EMUs
            rel_id: Relationship ID for the image
            shape_id: Unique shape ID
            name: Name for the picture

        Returns:
            The picture element
        """
        # Define namespaces for the picture element
        nsmap = {
            "a": NAMESPACES["a"],
            "r": NAMESPACES["r"],
            "p": NAMESPACES["p"],
        }

        p_ns = f"{{{NAMESPACES['p']}}}"
        a_ns = f"{{{NAMESPACES['a']}}}"
        r_ns = f"{{{NAMESPACES['r']}}}"

        # Create p:pic element
        pic = etree.Element(f"{p_ns}pic", nsmap=nsmap)

        # nvPicPr (Non-Visual Picture Properties)
        nv_pic_pr = etree.SubElement(pic, f"{p_ns}nvPicPr")

        c_nv_pr = etree.SubElement(
            nv_pic_pr, f"{p_ns}cNvPr", {"id": str(shape_id), "name": f"Picture {name}"}
        )

        etree.SubElement(nv_pic_pr, f"{p_ns}cNvPicPr")
        etree.SubElement(nv_pic_pr, f"{p_ns}nvPr")

        # blipFill
        blip_fill = etree.SubElement(pic, f"{p_ns}blipFill")

        blip = etree.SubElement(blip_fill, f"{a_ns}blip")
        blip.set(f"{r_ns}embed", rel_id)

        stretch = etree.SubElement(blip_fill, f"{a_ns}stretch")
        etree.SubElement(stretch, f"{a_ns}fillRect")

        # spPr (Shape Properties)
        sp_pr = etree.SubElement(pic, f"{p_ns}spPr")

        xfrm = etree.SubElement(sp_pr, f"{a_ns}xfrm")
        etree.SubElement(
            xfrm,
            f"{a_ns}off",
            {"x": str(dimensions["x"]), "y": str(dimensions["y"])},
        )
        etree.SubElement(
            xfrm,
            f"{a_ns}ext",
            {"cx": str(dimensions["cx"]), "cy": str(dimensions["cy"])},
        )

        etree.SubElement(sp_pr, f"{a_ns}prstGeom", {"prst": "rect"})

        return pic

    def get_replacement_summary(self) -> dict:
        """
        Get a summary of image replacements made.

        Returns:
            Dictionary with replacement statistics
        """
        return {
            "total_images": len(self.images_added),
            "images": self.images_added,
        }


def replace_image_placeholders(
    slide_root: etree._Element,
    slide_path: str,
    context: dict[str, Any],
    working_dir: str,
    strict: bool = False,
    slide_num: int = None,
) -> etree._Element:
    """
    Convenience function to replace image placeholders in a slide.

    Args:
        slide_root: Root element of a slide XML
        slide_path: Path to the slide XML file
        context: Dictionary of values (image paths) to substitute
        working_dir: Path to the extracted PPTX working directory
        strict: If True, raise error on missing images
        slide_num: Slide number for error reporting

    Returns:
        The modified slide root
    """
    replacer = ImageReplacer(context, working_dir, strict)
    return replacer.replace_in_slide(slide_root, slide_path, slide_num)
