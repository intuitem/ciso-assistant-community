"""Server-side PDF rendering with Typst.

Data reaches the template as a JSON string through `sys.inputs`: no Python
object is ever in scope, so a template cannot reach the ORM, the filesystem or
the network the way a Jinja or Django template can. The compilation root is a
throwaway directory holding only the files we put in it, which bounds `read()`
and `image()` to our own inputs.
"""

import json
import tempfile
from pathlib import Path

import structlog
import typst

logger = structlog.get_logger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent / "typst"
VENDORED_PACKAGES = TEMPLATE_DIR / "packages"
DEFAULT_LOCALE = "en"

# Render time grows faster than linearly with label length (1 MB took minutes).
MERMAID_MAX_SOURCE_CHARS = 20_000
MERMAID_TEMPLATE = """#import "@preview/merman:0.3.0": mermaid
#set page(width: auto, height: auto, margin: 0pt, fill: none)
#mermaid(sys.inputs.source, error-mode: "panic")
"""


def localized_template(stem: str, lang: str) -> str:
    """`stem` for `lang`, falling back to English when that locale has no file.

    Templates are self-contained per locale (see `core/typst/audit_report_en.typ`),
    so an unauthored locale falls back as a whole document rather than rendering
    half-translated.
    """
    candidate = f"{stem}_{(lang or DEFAULT_LOCALE).split('-')[0].lower()}.typ"
    if (TEMPLATE_DIR / candidate).is_file():
        return candidate
    return f"{stem}_{DEFAULT_LOCALE}.typ"


def render_pdf(
    template_name: str,
    data: dict,
    images: dict[str, bytes] | None = None,
    pdf_standards: list[str] | None = None,
) -> bytes:
    """Compile a Typst template against `data`, returning PDF bytes.

    `images` maps a bare filename to its bytes; the template references it by
    that name. Package paths are pinned to an empty directory so an import
    cannot silently pull code from the network at render time.
    """
    template = (TEMPLATE_DIR / template_name).read_bytes()

    with tempfile.TemporaryDirectory() as root:
        root_path = Path(root)
        entrypoint = root_path / "main.typ"
        entrypoint.write_bytes(template)

        for name, payload in (images or {}).items():
            target = root_path / Path(name).name
            target.write_bytes(payload)

        packages = root_path / "packages"
        packages.mkdir()

        return typst.compile(
            entrypoint,
            root=root_path,
            format="pdf",
            sys_inputs={"data": json.dumps(data, default=str)},
            pdf_standards=pdf_standards or [],
            package_path=str(packages),
            package_cache_path=str(packages),
        )


def render_mermaid_svg(source: str) -> bytes | None:
    """Render Mermaid source to SVG with the vendored merman package, or None if it fails."""
    if len(source) > MERMAID_MAX_SOURCE_CHARS:
        logger.warning("Mermaid diagram too large to render", chars=len(source))
        return None
    with tempfile.TemporaryDirectory() as root:
        entrypoint = Path(root) / "main.typ"
        entrypoint.write_text(MERMAID_TEMPLATE)
        try:
            return typst.compile(
                entrypoint,
                root=root,
                format="svg",
                sys_inputs={"source": source},
                package_path=str(VENDORED_PACKAGES),
                package_cache_path=root,
            )
        except Exception as e:
            logger.warning("Mermaid diagram could not be rendered", error=e)
            return None
