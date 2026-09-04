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

import typst

TEMPLATE_DIR = Path(__file__).resolve().parent / "typst"


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
