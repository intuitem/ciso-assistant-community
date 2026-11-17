"""Exports specific to a framework, such as a publisher's official
self-assessment template.

Base models and views only go through this registry. Each export registers
itself from its own module, which CoreConfig.ready() imports.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ExportFile:
    content: bytes
    filename: str
    content_type: str


@dataclass(frozen=True)
class FrameworkExport:
    ref_id: str  # route segment of the export, unique
    title: str  # translation keys of the export menu entry
    description: str
    format: str  # file format shown in the export menu, e.g. "XLSX"
    supports: Callable[[object], bool]  # (audit) -> whether it applies
    build: Callable[[object], ExportFile]  # (audit) -> the exported file


_registry: dict[str, FrameworkExport] = {}


def register(export: FrameworkExport) -> None:
    # The export route only matches these ids.
    if not re.fullmatch(r"[\w-]+", export.ref_id):
        raise ValueError(f"Invalid framework export id {export.ref_id!r}")
    if export.ref_id in _registry:
        raise ValueError(f"Framework export {export.ref_id!r} is already registered")
    _registry[export.ref_id] = export


def get(ref_id: str) -> FrameworkExport | None:
    return _registry.get(ref_id)


def available_for(audit) -> list[FrameworkExport]:
    """The exports an audit supports, in registration order."""
    return [export for export in _registry.values() if export.supports(audit)]
