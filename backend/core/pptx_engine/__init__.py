"""
PPTX Template Engine

A PowerPoint template engine that processes PPTX files with placeholder markup.

Supported placeholders:
- {{variable}} - Text replacement
- {{image:variable}} - Image insertion
- {{#each collection}}...{{/each}} - Table row iteration
- {{#slide collection}}...{{/slide}} - Slide duplication

Usage:
    from core.pptx_engine import PPTXTemplateEngine

    engine = PPTXTemplateEngine()
    output_path = engine.process(
        template_path='template.pptx',
        context={'name': 'John', 'logo': '/path/to/logo.png'}
    )
"""

from .engine import PPTXTemplateEngine
from .exceptions import (
    PPTXTemplateError,
    InvalidTemplateError,
    PlaceholderError,
    MissingContextError,
    ImageError,
)

__all__ = [
    "PPTXTemplateEngine",
    "PPTXTemplateError",
    "InvalidTemplateError",
    "PlaceholderError",
    "MissingContextError",
    "ImageError",
]
