"""
Text normalizer for handling fragmented placeholders in PPTX XML.

PowerPoint often splits text across multiple runs (<a:r> elements) even within
a single word or placeholder. This module provides functionality to normalize
these runs so that placeholders can be properly detected and replaced.

Example of fragmented text:
    <a:p>
      <a:r><a:t>{{</a:t></a:r>
      <a:r><a:rPr b="1"/><a:t>user</a:t></a:r>
      <a:r><a:t>}}</a:t></a:r>
    </a:p>

After normalization:
    <a:p>
      <a:r><a:t>{{user}}</a:t></a:r>
    </a:p>
"""

import re
from copy import deepcopy
from lxml import etree

from .constants import NAMESPACES, PLACEHOLDER_PATTERN


class TextNormalizer:
    """
    Normalizes text runs in PPTX paragraphs to enable placeholder detection.

    The normalizer merges adjacent text runs that contain parts of placeholders,
    preserving the formatting from the first run in each merged group.
    """

    def __init__(self):
        self.a_ns = f"{{{NAMESPACES['a']}}}"

    def normalize_slide(self, slide_root: etree._Element) -> etree._Element:
        """
        Normalize all paragraphs in a slide.

        Args:
            slide_root: Root element of a slide XML

        Returns:
            The modified slide root (modified in place)
        """
        # Find all paragraph elements
        for p_elem in slide_root.iter(f"{self.a_ns}p"):
            self.normalize_paragraph(p_elem)

        return slide_root

    def normalize_paragraph(self, p_element: etree._Element) -> None:
        """
        Normalize text runs within a paragraph to merge fragmented placeholders.

        This method modifies the paragraph element in place.

        Args:
            p_element: A DrawingML paragraph element (a:p)
        """
        runs = list(p_element.findall(f"{self.a_ns}r"))

        if len(runs) <= 1:
            return  # Nothing to normalize

        # Build a list of (run_element, text, start_pos, end_pos)
        run_info = []
        current_pos = 0

        for run in runs:
            t_elem = run.find(f"{self.a_ns}t")
            text = t_elem.text if t_elem is not None and t_elem.text else ""
            run_info.append(
                {
                    "element": run,
                    "t_element": t_elem,
                    "text": text,
                    "start": current_pos,
                    "end": current_pos + len(text),
                }
            )
            current_pos += len(text)

        # Get full concatenated text
        full_text = "".join(r["text"] for r in run_info)

        # Find all placeholders and their positions
        placeholder_spans = []
        for match in re.finditer(PLACEHOLDER_PATTERN, full_text):
            placeholder_spans.append((match.start(), match.end()))

        if not placeholder_spans:
            return  # No placeholders, nothing to normalize

        # Find runs that need to be merged for each placeholder
        merge_groups = []
        for ph_start, ph_end in placeholder_spans:
            # Find all runs that overlap with this placeholder
            overlapping_runs = []
            for i, info in enumerate(run_info):
                # Check if run overlaps with placeholder span
                if info["end"] > ph_start and info["start"] < ph_end:
                    overlapping_runs.append(i)

            if len(overlapping_runs) > 1:
                merge_groups.append(overlapping_runs)

        if not merge_groups:
            return  # All placeholders are contained in single runs

        # Merge runs in reverse order to preserve indices
        # First, flatten and deduplicate merge groups
        runs_to_process = self._consolidate_merge_groups(merge_groups)

        for group in reversed(runs_to_process):
            self._merge_run_group(p_element, run_info, group)

    def _consolidate_merge_groups(self, groups: list[list[int]]) -> list[list[int]]:
        """
        Consolidate overlapping merge groups into non-overlapping sequences.

        Args:
            groups: List of run index lists to merge

        Returns:
            Consolidated list of run index lists
        """
        if not groups:
            return []

        # Sort groups by first index
        sorted_groups = sorted(groups, key=lambda g: g[0])

        consolidated = []
        current = list(sorted_groups[0])

        for group in sorted_groups[1:]:
            # Check if this group overlaps with or is adjacent to current
            if group[0] <= current[-1] + 1:
                # Merge groups
                current = sorted(set(current + group))
            else:
                consolidated.append(current)
                current = list(group)

        consolidated.append(current)
        return consolidated

    def _merge_run_group(
        self,
        p_element: etree._Element,
        run_info: list[dict],
        indices: list[int],
    ) -> None:
        """
        Merge a group of runs into the first run.

        Args:
            p_element: Parent paragraph element
            run_info: List of run information dictionaries
            indices: Indices of runs to merge
        """
        if len(indices) < 2:
            return

        first_idx = indices[0]
        first_run = run_info[first_idx]["element"]
        first_t = run_info[first_idx]["t_element"]

        # Concatenate all text
        merged_text = "".join(run_info[i]["text"] for i in indices)

        # Update the first run's text
        if first_t is not None:
            first_t.text = merged_text
            # Preserve whitespace
            first_t.set(
                f"{{{NAMESPACES.get('xml', 'http://www.w3.org/XML/1998/namespace')}}}space",
                "preserve",
            )
        else:
            # Create text element if it doesn't exist
            first_t = etree.SubElement(first_run, f"{self.a_ns}t")
            first_t.text = merged_text

        # Remove the other runs (in reverse order to preserve indices)
        for idx in reversed(indices[1:]):
            run_elem = run_info[idx]["element"]
            p_element.remove(run_elem)

    def denormalize_paragraph(
        self,
        p_element: etree._Element,
        original_structure: list[dict],
    ) -> None:
        """
        Attempt to restore original run structure after replacement.

        This is optional and can help preserve formatting better in some cases.
        Currently not implemented - the normalized structure is usually acceptable.

        Args:
            p_element: The paragraph element to denormalize
            original_structure: The original run structure information
        """
        # TODO: Implement if needed for better formatting preservation
        pass


def normalize_xml_content(xml_root: etree._Element) -> etree._Element:
    """
    Convenience function to normalize all text in an XML document.

    Args:
        xml_root: Root element of the XML document

    Returns:
        The modified root element
    """
    normalizer = TextNormalizer()
    return normalizer.normalize_slide(xml_root)
