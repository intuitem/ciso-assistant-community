"""
Loop processor for PPTX templates.

Handles:
- {{#each collection}}...{{/each}} for table row iteration
- {{#slide collection}}...{{/slide}} for slide duplication
"""

import os
import re
import shutil
from copy import deepcopy
from typing import Any
from lxml import etree

from ..constants import (
    NAMESPACES,
    EACH_START_PATTERN,
    EACH_END_PATTERN,
    SLIDE_START_PATTERN,
    SLIDE_END_PATTERN,
    SLIDES_DIR,
)
from ..exceptions import LoopError, MissingContextError
from ..utils import resolve_context_value, parse_xml, write_xml, NOT_FOUND


class LoopProcessor:
    """
    Processes loop constructs in PPTX templates.

    Supports two types of loops:
    1. Table row loops ({{#each}}) - duplicates table rows for each item
    2. Slide loops ({{#slide}}) - duplicates entire slides for each item
    """

    def __init__(self, context: dict[str, Any], working_dir: str, strict: bool = False):
        """
        Initialize the loop processor.

        Args:
            context: Dictionary of values to substitute
            working_dir: Path to the extracted PPTX working directory
            strict: If True, raise error on missing collections
        """
        self.context = context
        self.working_dir = working_dir
        self.strict = strict
        self.a_ns = f"{{{NAMESPACES['a']}}}"
        self.p_ns = f"{{{NAMESPACES['p']}}}"
        # Track loops processed
        self.loops_processed: list[dict] = []

    def process_table_loops(
        self, slide_root: etree._Element, slide_num: int = None
    ) -> etree._Element:
        """
        Process {{#each}} loops in tables.

        Args:
            slide_root: Root element of a slide XML
            slide_num: Slide number for error reporting

        Returns:
            The modified slide root
        """
        # Find all tables in the slide
        for tbl in slide_root.iter(f"{self.a_ns}tbl"):
            self._process_table(tbl, slide_num)

        return slide_root

    def _process_table(
        self, tbl_element: etree._Element, slide_num: int = None
    ) -> None:
        """
        Process a single table for {{#each}} loops.

        Args:
            tbl_element: The table element
            slide_num: Slide number for error reporting
        """
        rows = list(tbl_element.findall(f"{self.a_ns}tr"))

        # Find rows with #each markers
        i = 0
        while i < len(rows):
            row = rows[i]
            row_text = self._get_row_text(row)

            # Check for #each start
            match = re.search(EACH_START_PATTERN, row_text)
            if match:
                collection_name = match.group(1).strip()

                # Find the closing {{/each}}
                end_row_idx = self._find_each_end(rows, i + 1)
                if end_row_idx is None:
                    raise LoopError(
                        "Unclosed {{#each}} loop",
                        loop_var=collection_name,
                        slide_num=slide_num,
                    )

                # Get the collection from context
                collection = resolve_context_value(self.context, collection_name)

                if collection is NOT_FOUND:
                    if self.strict:
                        raise MissingContextError(collection_name, slide_num)
                    collection = []
                elif collection is None:
                    collection = []

                if not isinstance(collection, (list, tuple)):
                    raise LoopError(
                        f"Expected list for {{{{#each {collection_name}}}}}, got {type(collection).__name__}",
                        loop_var=collection_name,
                        slide_num=slide_num,
                    )

                # Get template rows (between #each and /each, exclusive of markers)
                template_rows = rows[i + 1 : end_row_idx]

                # Check if the #each marker is alone in its row or mixed with content
                each_row_has_only_marker = self._row_has_only_marker(
                    row, EACH_START_PATTERN
                )
                end_row_has_only_marker = self._row_has_only_marker(
                    rows[end_row_idx], EACH_END_PATTERN
                )

                # If markers are mixed with content, the row itself is the template
                if not each_row_has_only_marker:
                    template_rows = [row]
                    # Remove the #each marker from the template
                    self._remove_marker_from_row(row, EACH_START_PATTERN)

                # Generate new rows for each item in collection
                new_rows = []
                for idx, item in enumerate(collection):
                    # Create item context with loop variables
                    item_context = self._create_item_context(item, idx, len(collection))

                    for template_row in template_rows:
                        # Deep copy the template row
                        new_row = deepcopy(template_row)
                        # Replace placeholders in the new row
                        self._replace_in_row(new_row, item_context)
                        new_rows.append(new_row)

                # Calculate positions for insertion/removal
                # We need to find the actual index in tbl_element's children (not just rows)
                # because tbl_element also contains tblPr, tblGrid, etc.
                all_children = list(tbl_element)
                row_element_index = (
                    all_children.index(row) if row in all_children else -1
                )

                if each_row_has_only_marker:
                    # Remove the #each marker row
                    tbl_element.remove(row)
                    insert_position = row_element_index  # Use actual child index
                else:
                    # The #each row is part of template, already included in new_rows
                    tbl_element.remove(row)
                    insert_position = row_element_index  # Use actual child index

                # Remove template rows (if separate from #each row)
                if each_row_has_only_marker:
                    for template_row in template_rows:
                        if template_row in list(tbl_element):
                            tbl_element.remove(template_row)

                # Remove the /each marker row
                # Need to refetch as indices changed
                current_rows = list(tbl_element.findall(f"{self.a_ns}tr"))
                for row_to_check in current_rows:
                    if re.search(EACH_END_PATTERN, self._get_row_text(row_to_check)):
                        if end_row_has_only_marker:
                            tbl_element.remove(row_to_check)
                        else:
                            self._remove_marker_from_row(row_to_check, EACH_END_PATTERN)
                        break

                # Insert new rows
                for j, new_row in enumerate(new_rows):
                    tbl_element.insert(insert_position + j, new_row)

                # Track the loop
                self.loops_processed.append(
                    {
                        "type": "each",
                        "collection": collection_name,
                        "items_count": len(collection),
                        "rows_generated": len(new_rows),
                        "slide": slide_num,
                    }
                )

                # Update rows list and continue
                rows = list(tbl_element.findall(f"{self.a_ns}tr"))
                i += len(new_rows)
            else:
                i += 1

    def _get_row_text(self, row_element: etree._Element) -> str:
        """Extract all text from a table row."""
        texts = []
        for t_elem in row_element.iter(f"{self.a_ns}t"):
            if t_elem.text:
                texts.append(t_elem.text)
        return "".join(texts)

    def _find_each_end(self, rows: list, start_idx: int) -> int | None:
        """Find the index of the row containing {{/each}}."""
        for i in range(start_idx, len(rows)):
            if re.search(EACH_END_PATTERN, self._get_row_text(rows[i])):
                return i
        return None

    def _row_has_only_marker(self, row: etree._Element, pattern: str) -> bool:
        """Check if a row contains only a loop marker and whitespace."""
        text = self._get_row_text(row).strip()
        # Remove the marker and check if anything significant remains
        remaining = re.sub(pattern, "", text).strip()
        return len(remaining) == 0

    def _remove_marker_from_row(self, row: etree._Element, pattern: str) -> None:
        """Remove a loop marker from all text elements in a row."""
        for t_elem in row.iter(f"{self.a_ns}t"):
            if t_elem.text:
                t_elem.text = re.sub(pattern, "", t_elem.text)

    def _create_item_context(self, item: Any, index: int, total: int) -> dict[str, Any]:
        """
        Create a context dictionary for a loop item.

        Args:
            item: The item (can be dict or object)
            index: Zero-based index
            total: Total number of items

        Returns:
            Context dictionary with item properties and loop metadata
        """
        # Start with item properties
        if isinstance(item, dict):
            context = dict(item)
        else:
            # Try to convert object to dict
            context = {}
            for attr in dir(item):
                if not attr.startswith("_"):
                    try:
                        context[attr] = getattr(item, attr)
                    except Exception:
                        pass

        # Add loop metadata
        context["_index"] = index
        context["_index1"] = index + 1  # 1-based index
        context["_first"] = index == 0
        context["_last"] = index == total - 1
        context["_total"] = total

        return context

    def _replace_in_row(self, row: etree._Element, context: dict[str, Any]) -> None:
        """
        Replace placeholders in a table row.

        Args:
            row: The row element
            context: Context dictionary for replacement
        """
        from .text import TextReplacer

        replacer = TextReplacer(context, strict=False)

        for t_elem in row.iter(f"{self.a_ns}t"):
            if t_elem.text:
                t_elem.text = replacer._replace_in_text(t_elem.text)

    def find_slide_loops(self) -> list[dict]:
        """
        Find all slides with {{#slide}} markers.

        Returns:
            List of dictionaries with slide info and collection names
        """
        slides_dir = os.path.join(self.working_dir, SLIDES_DIR)
        slide_loops = []

        if not os.path.exists(slides_dir):
            return slide_loops

        slide_files = sorted(
            [
                f
                for f in os.listdir(slides_dir)
                if f.startswith("slide") and f.endswith(".xml")
            ]
        )

        for slide_file in slide_files:
            slide_path = os.path.join(slides_dir, slide_file)
            slide_root = parse_xml(slide_path)

            # Get all text from slide
            slide_text = ""
            for t_elem in slide_root.iter(f"{self.a_ns}t"):
                if t_elem.text:
                    slide_text += t_elem.text

            # Check for #slide marker
            match = re.search(SLIDE_START_PATTERN, slide_text)
            if match:
                collection_name = match.group(1).strip()

                # Verify closing marker exists
                if not re.search(SLIDE_END_PATTERN, slide_text):
                    # Extract slide number from filename
                    slide_num = int(re.search(r"slide(\d+)", slide_file).group(1))
                    raise LoopError(
                        "Unclosed {{#slide}} loop",
                        loop_var=collection_name,
                        slide_num=slide_num,
                    )

                slide_loops.append(
                    {
                        "file": slide_file,
                        "path": slide_path,
                        "collection": collection_name,
                    }
                )

        return slide_loops

    def process_slide_loop(
        self, slide_info: dict, presentation_manager: "PresentationManager"
    ) -> list[str]:
        """
        Process a single {{#slide}} loop, duplicating the slide for each item.

        Args:
            slide_info: Dictionary with slide file info and collection name
            presentation_manager: Manager for presentation.xml modifications

        Returns:
            List of paths to new slide files created
        """
        collection_name = slide_info["collection"]
        template_path = slide_info["path"]

        # Get the collection
        collection = resolve_context_value(self.context, collection_name)

        if collection is NOT_FOUND:
            if self.strict:
                raise MissingContextError(collection_name)
            collection = []
        elif collection is None:
            collection = []

        if not isinstance(collection, (list, tuple)):
            raise LoopError(
                f"Expected list for {{{{#slide {collection_name}}}}}, "
                f"got {type(collection).__name__}",
                loop_var=collection_name,
            )

        if len(collection) == 0:
            # Remove the template slide if collection is empty
            os.remove(template_path)
            # Also remove rels file if exists
            rels_path = self._get_slide_rels_path(template_path)
            if os.path.exists(rels_path):
                os.remove(rels_path)
            return []

        new_slide_paths = []
        slides_dir = os.path.dirname(template_path)

        # Parse template
        template_root = parse_xml(template_path)

        # Remove the #slide markers from template
        self._remove_slide_markers(template_root)

        for idx, item in enumerate(collection):
            # Create item context
            item_context = self._create_item_context(item, idx, len(collection))

            # Deep copy template
            slide_root = deepcopy(template_root)

            # Replace placeholders
            self._replace_in_slide(slide_root, item_context)

            # Determine new slide path
            if idx == 0:
                # Reuse the original template file
                new_path = template_path
            else:
                # Create new slide file
                new_filename = self._generate_slide_filename(slides_dir)
                new_path = os.path.join(slides_dir, new_filename)

                # Copy rels file if exists
                template_rels = self._get_slide_rels_path(template_path)
                if os.path.exists(template_rels):
                    new_rels = self._get_slide_rels_path(new_path)
                    os.makedirs(os.path.dirname(new_rels), exist_ok=True)
                    shutil.copy2(template_rels, new_rels)

                # Register new slide in presentation
                presentation_manager.add_slide(new_filename)

            # Write slide
            write_xml(slide_root, new_path)
            new_slide_paths.append(new_path)

        # Track the loop
        self.loops_processed.append(
            {
                "type": "slide",
                "collection": collection_name,
                "items_count": len(collection),
                "slides_generated": len(new_slide_paths),
            }
        )

        return new_slide_paths

    def _remove_slide_markers(self, slide_root: etree._Element) -> None:
        """Remove {{#slide}} and {{/slide}} markers from slide."""
        for t_elem in slide_root.iter(f"{self.a_ns}t"):
            if t_elem.text:
                t_elem.text = re.sub(SLIDE_START_PATTERN, "", t_elem.text)
                t_elem.text = re.sub(SLIDE_END_PATTERN, "", t_elem.text)

    def _replace_in_slide(
        self, slide_root: etree._Element, context: dict[str, Any]
    ) -> None:
        """Replace placeholders in a slide."""
        from .text import TextReplacer

        replacer = TextReplacer(context, strict=False)

        for t_elem in slide_root.iter(f"{self.a_ns}t"):
            if t_elem.text:
                t_elem.text = replacer._replace_in_text(t_elem.text)

    def _get_slide_rels_path(self, slide_path: str) -> str:
        """Get the path to a slide's .rels file."""
        slide_dir = os.path.dirname(slide_path)
        slide_name = os.path.basename(slide_path)
        return os.path.join(slide_dir, "_rels", f"{slide_name}.rels")

    def _generate_slide_filename(self, slides_dir: str) -> str:
        """Generate a unique slide filename."""
        existing = [
            f
            for f in os.listdir(slides_dir)
            if f.startswith("slide") and f.endswith(".xml")
        ]
        max_num = 0
        for f in existing:
            match = re.search(r"slide(\d+)\.xml", f)
            if match:
                max_num = max(max_num, int(match.group(1)))
        return f"slide{max_num + 1}.xml"

    def get_processing_summary(self) -> dict:
        """Get a summary of loops processed."""
        return {
            "total_loops": len(self.loops_processed),
            "loops": self.loops_processed,
        }


class PresentationManager:
    """
    Manages presentation.xml for slide additions and ordering.
    """

    def __init__(self, working_dir: str):
        """
        Initialize the presentation manager.

        Args:
            working_dir: Path to the extracted PPTX working directory
        """
        self.working_dir = working_dir
        self.presentation_path = os.path.join(working_dir, "ppt", "presentation.xml")
        self.rels_path = os.path.join(
            working_dir, "ppt", "_rels", "presentation.xml.rels"
        )
        self.p_ns = f"{{{NAMESPACES['p']}}}"
        self.r_ns = f"{{{NAMESPACES['r']}}}"

    def add_slide(self, slide_filename: str) -> str:
        """
        Add a new slide to the presentation.

        Args:
            slide_filename: Name of the slide file (e.g., "slide5.xml")

        Returns:
            The relationship ID for the new slide
        """
        # Add relationship
        rel_id = self._add_slide_relationship(slide_filename)

        # Add to slide list in presentation.xml
        self._add_to_slide_list(rel_id)

        # Update content types
        self._ensure_slide_content_type(slide_filename)

        return rel_id

    def _add_slide_relationship(self, slide_filename: str) -> str:
        """Add a relationship for the new slide."""
        rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"

        tree = etree.parse(self.rels_path)
        root = tree.getroot()

        # Find next rId
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
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide",
                "Target": f"slides/{slide_filename}",
            },
        )

        tree.write(self.rels_path, xml_declaration=True, encoding="UTF-8")
        return new_rel_id

    def _add_to_slide_list(self, rel_id: str) -> None:
        """Add the slide to the slide list in presentation.xml."""
        tree = etree.parse(self.presentation_path)
        root = tree.getroot()

        # Find sldIdLst
        sld_id_lst = root.find(f".//{self.p_ns}sldIdLst")

        if sld_id_lst is None:
            # Create if not exists
            sld_id_lst = etree.SubElement(root, f"{self.p_ns}sldIdLst")

        # Find next slide ID
        existing_ids = []
        for sld_id in sld_id_lst.findall(f"{self.p_ns}sldId"):
            try:
                existing_ids.append(int(sld_id.get("id", 0)))
            except ValueError:
                pass

        # PowerPoint slide IDs typically start at 256
        next_id = max(existing_ids, default=255) + 1

        # Add new slide ID
        new_sld_id = etree.SubElement(sld_id_lst, f"{self.p_ns}sldId")
        new_sld_id.set("id", str(next_id))
        new_sld_id.set(f"{self.r_ns}id", rel_id)

        tree.write(self.presentation_path, xml_declaration=True, encoding="UTF-8")

    def _ensure_slide_content_type(self, slide_filename: str) -> None:
        """Ensure the content type for the new slide is registered."""
        content_types_path = os.path.join(self.working_dir, "[Content_Types].xml")

        tree = etree.parse(content_types_path)
        root = tree.getroot()
        ct_ns = "http://schemas.openxmlformats.org/package/2006/content-types"

        # Check if this specific slide is already registered
        part_name = f"/ppt/slides/{slide_filename}"

        for override in root.findall(f"{{{ct_ns}}}Override"):
            if override.get("PartName") == part_name:
                return  # Already registered

        # Add override for new slide
        etree.SubElement(
            root,
            f"{{{ct_ns}}}Override",
            {
                "PartName": part_name,
                "ContentType": "application/vnd.openxmlformats-officedocument.presentationml.slide+xml",
            },
        )

        tree.write(
            content_types_path, xml_declaration=True, encoding="UTF-8", standalone=True
        )
