"""
Constants and XML namespaces for PPTX processing.
"""

# XML Namespaces used in PPTX files
NAMESPACES = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "dgm": "http://schemas.openxmlformats.org/drawingml/2006/diagram",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

# Relationship types
REL_TYPE_IMAGE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
)
REL_TYPE_SLIDE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
)
REL_TYPE_SLIDE_LAYOUT = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout"
)

# Content types for images
IMAGE_CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
}

# Placeholder patterns
PLACEHOLDER_PATTERN = r"\{\{([^}]+)\}\}"  # Matches {{anything}}
IMAGE_PLACEHOLDER_PATTERN = r"\{\{image:([^}]+)\}\}"  # Matches {{image:name}}
EACH_START_PATTERN = r"\{\{#each\s+([^}]+)\}\}"  # Matches {{#each collection}}
EACH_END_PATTERN = r"\{\{/each\}\}"  # Matches {{/each}}
SLIDE_START_PATTERN = r"\{\{#slide\s+([^}]+)\}\}"  # Matches {{#slide collection}}
SLIDE_END_PATTERN = r"\{\{/slide\}\}"  # Matches {{/slide}}

# PPTX file paths
CONTENT_TYPES_PATH = "[Content_Types].xml"
PRESENTATION_PATH = "ppt/presentation.xml"
PRESENTATION_RELS_PATH = "ppt/_rels/presentation.xml.rels"
SLIDES_DIR = "ppt/slides"
MEDIA_DIR = "ppt/media"

# EMU (English Metric Units) conversion
# PowerPoint uses EMUs for measurements: 1 inch = 914400 EMUs
EMU_PER_INCH = 914400
EMU_PER_CM = 360000
EMU_PER_PT = 12700
