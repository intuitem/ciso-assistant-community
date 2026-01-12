"""
Main PPTX Template Engine.

Orchestrates the template processing workflow:
1. Extract PPTX to working directory
2. Process slide loops (duplicate slides)
3. For each slide:
   a. Normalize text runs
   b. Process table loops
   c. Replace image placeholders
   d. Replace text placeholders
4. Repackage as PPTX
"""

import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, BinaryIO

from .constants import NAMESPACES, SLIDES_DIR
from .exceptions import InvalidTemplateError, PPTXTemplateError
from .normalizer import TextNormalizer
from .replacers.text import TextReplacer
from .replacers.image import ImageReplacer
from .replacers.loops import LoopProcessor, PresentationManager
from .utils import parse_xml, write_xml, register_namespaces


class PPTXTemplateEngine:
    """
    PowerPoint template engine that processes PPTX files with placeholder markup.

    Supported placeholders:
    - {{variable}} - Text replacement
    - {{image:variable}} - Image insertion
    - {{#each collection}}...{{/each}} - Table row iteration
    - {{#slide collection}}...{{/slide}} - Slide duplication

    Usage:
        engine = PPTXTemplateEngine()
        output_path = engine.process(
            template_path='template.pptx',
            context={'name': 'John', 'logo': '/path/to/logo.png'}
        )
    """

    def __init__(self, strict: bool = False):
        """
        Initialize the template engine.

        Args:
            strict: If True, raise errors for missing context values.
                   If False, leave placeholders unchanged.
        """
        self.strict = strict
        self.a_ns = f"{{{NAMESPACES['a']}}}"
        # Register namespaces to preserve prefixes
        register_namespaces()

    def process(
        self,
        template_path: str | Path | BinaryIO,
        context: dict[str, Any],
        output_path: str | Path = None,
    ) -> str:
        """
        Process a template with the given context and generate output PPTX.

        Args:
            template_path: Path to template PPTX file or file-like object
            context: Dictionary of values for placeholder substitution
            output_path: Optional path for output file. If not provided,
                        a temporary file will be created.

        Returns:
            Path to the generated PPTX file

        Raises:
            InvalidTemplateError: If template is not a valid PPTX
            PlaceholderError: If there's an error with placeholder syntax
            MissingContextError: If strict mode and required value is missing
            ImageError: If there's an error processing images
        """
        # Validate template
        self._validate_template(template_path)

        # Create working directory
        working_dir = tempfile.mkdtemp(prefix="pptx_template_")

        try:
            # Extract template
            self._extract_template(template_path, working_dir)

            # Process the template
            self._process_template(working_dir, context)

            # Create output file
            if output_path is None:
                output_fd, output_path = tempfile.mkstemp(suffix=".pptx")
                os.close(output_fd)

            output_path = str(output_path)

            # Repackage as PPTX
            self._create_pptx(working_dir, output_path)

            return output_path

        finally:
            # Clean up working directory
            shutil.rmtree(working_dir, ignore_errors=True)

    def process_to_bytes(
        self,
        template_path: str | Path | BinaryIO,
        context: dict[str, Any],
    ) -> bytes:
        """
        Process a template and return the result as bytes.

        Args:
            template_path: Path to template PPTX file or file-like object
            context: Dictionary of values for placeholder substitution

        Returns:
            The generated PPTX file as bytes
        """
        output_path = self.process(template_path, context)
        try:
            with open(output_path, "rb") as f:
                return f.read()
        finally:
            os.unlink(output_path)

    def extract_placeholders(
        self, template_path: str | Path | BinaryIO
    ) -> dict[str, list]:
        """
        Extract all placeholders from a template without processing.

        Useful for template validation and documentation.

        Args:
            template_path: Path to template PPTX file

        Returns:
            Dictionary with placeholder types as keys and lists of names
        """
        self._validate_template(template_path)

        working_dir = tempfile.mkdtemp(prefix="pptx_extract_")

        try:
            self._extract_template(template_path, working_dir)

            placeholders = {
                "text": [],
                "image": [],
                "each": [],
                "slide": [],
            }

            slides_dir = os.path.join(working_dir, SLIDES_DIR)

            if not os.path.exists(slides_dir):
                return placeholders

            for slide_file in os.listdir(slides_dir):
                if not slide_file.endswith(".xml"):
                    continue

                slide_path = os.path.join(slides_dir, slide_file)
                slide_root = parse_xml(slide_path)

                # Extract all text
                for t_elem in slide_root.iter(f"{self.a_ns}t"):
                    if t_elem.text:
                        text = t_elem.text

                        # Find text placeholders
                        for match in re.finditer(r"\{\{([^}#/]+)\}\}", text):
                            name = match.group(1)
                            if name.startswith("image:"):
                                img_name = name[6:]
                                if img_name not in placeholders["image"]:
                                    placeholders["image"].append(img_name)
                            elif name not in placeholders["text"]:
                                placeholders["text"].append(name)

                        # Find each loops
                        for match in re.finditer(r"\{\{#each\s+([^}]+)\}\}", text):
                            name = match.group(1).strip()
                            if name not in placeholders["each"]:
                                placeholders["each"].append(name)

                        # Find slide loops
                        for match in re.finditer(r"\{\{#slide\s+([^}]+)\}\}", text):
                            name = match.group(1).strip()
                            if name not in placeholders["slide"]:
                                placeholders["slide"].append(name)

            return placeholders

        finally:
            shutil.rmtree(working_dir, ignore_errors=True)

    def _validate_template(self, template_path: str | Path | BinaryIO) -> None:
        """Validate that the template is a valid PPTX file."""
        if hasattr(template_path, "read"):
            # File-like object - check if it's a valid zip
            try:
                template_path.seek(0)
                if not zipfile.is_zipfile(template_path):
                    raise InvalidTemplateError("File is not a valid PPTX (not a ZIP)")
                template_path.seek(0)
            except Exception as e:
                raise InvalidTemplateError(str(e))
        else:
            template_path = str(template_path)
            if not os.path.exists(template_path):
                raise InvalidTemplateError("Template file not found", template_path)
            if not zipfile.is_zipfile(template_path):
                raise InvalidTemplateError(
                    "File is not a valid PPTX (not a ZIP)", template_path
                )

    def _extract_template(
        self, template_path: str | Path | BinaryIO, working_dir: str
    ) -> None:
        """Extract PPTX contents to working directory."""
        if hasattr(template_path, "read"):
            template_path.seek(0)
            with zipfile.ZipFile(template_path, "r") as zf:
                zf.extractall(working_dir)
        else:
            with zipfile.ZipFile(str(template_path), "r") as zf:
                zf.extractall(working_dir)

    def _process_template(self, working_dir: str, context: dict[str, Any]) -> None:
        """Process all slides in the template."""
        # Initialize processors
        normalizer = TextNormalizer()
        text_replacer = TextReplacer(context, self.strict)
        image_replacer = ImageReplacer(context, working_dir, self.strict)
        loop_processor = LoopProcessor(context, working_dir, self.strict)
        presentation_manager = PresentationManager(working_dir)

        # First, handle slide loops (this may create new slides)
        slide_loops = loop_processor.find_slide_loops()
        for slide_info in slide_loops:
            loop_processor.process_slide_loop(slide_info, presentation_manager)

        # Now process all slides (including newly created ones)
        slides_dir = os.path.join(working_dir, SLIDES_DIR)

        if not os.path.exists(slides_dir):
            return

        slide_files = sorted(
            [
                f
                for f in os.listdir(slides_dir)
                if f.startswith("slide") and f.endswith(".xml")
            ]
        )

        for slide_file in slide_files:
            slide_path = os.path.join(slides_dir, slide_file)

            # Extract slide number for error reporting
            match = re.search(r"slide(\d+)", slide_file)
            slide_num = int(match.group(1)) if match else None

            # Parse slide XML
            slide_root = parse_xml(slide_path)

            # Step 1: Normalize text runs (merge fragmented placeholders)
            normalizer.normalize_slide(slide_root)

            # Step 2: Process table loops ({{#each}})
            loop_processor.process_table_loops(slide_root, slide_num)

            # Step 3: Replace image placeholders
            image_replacer.replace_in_slide(slide_root, slide_path, slide_num)

            # Step 4: Replace text placeholders
            # Re-parse after image replacement as DOM may have changed
            slide_root = (
                parse_xml(slide_path) if os.path.exists(slide_path) else slide_root
            )
            text_replacer.replace_in_slide(slide_root, slide_num)

            # Write modified slide
            write_xml(slide_root, slide_path)

    def _create_pptx(self, working_dir: str, output_path: str) -> None:
        """
        Create a PPTX file from the working directory.

        Uses the same compression settings as standard PPTX files.
        """
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(working_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, working_dir)
                    zf.write(file_path, arc_name)


# Convenience function for simple use cases
def render_template(
    template_path: str | Path,
    context: dict[str, Any],
    output_path: str | Path = None,
    strict: bool = False,
) -> str:
    """
    Render a PPTX template with the given context.

    This is a convenience function for simple use cases.

    Args:
        template_path: Path to template PPTX file
        context: Dictionary of values for placeholder substitution
        output_path: Optional path for output file
        strict: If True, raise errors for missing values

    Returns:
        Path to the generated PPTX file
    """
    engine = PPTXTemplateEngine(strict=strict)
    return engine.process(template_path, context, output_path)
