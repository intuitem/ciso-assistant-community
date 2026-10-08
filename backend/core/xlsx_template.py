"""Fill cells of an Excel template without rebuilding the workbook.

openpyxl rebuilds a workbook from what it understands and drops the rest
(charts, extended data validations...). Here only the target cells change, in
the worksheet XML; every other part of the file is copied as is.
"""

import io
import zipfile
from pathlib import PurePosixPath

from lxml import etree
from openpyxl.utils import column_index_from_string, get_column_letter

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELATIONSHIP = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_RELATIONSHIP = "http://schemas.openxmlformats.org/package/2006/relationships"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
WORKBOOK = "xl/workbook.xml"


def _tag(name: str) -> str:
    return f"{{{MAIN}}}{name}"


def _sheet_parts(archive: zipfile.ZipFile) -> dict[str, str]:
    """Worksheet part of each sheet name."""
    workbook = etree.fromstring(archive.read(WORKBOOK))
    relationships = etree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        rel.get("Id"): rel.get("Target")
        for rel in relationships.iter(f"{{{PACKAGE_RELATIONSHIP}}}Relationship")
    }
    parts = {}
    for sheet in workbook.iter(_tag("sheet")):
        target = targets[sheet.get(f"{{{RELATIONSHIP}}}id")]
        parts[sheet.get("name")] = (
            target.lstrip("/")
            if target.startswith("/")
            else str(PurePosixPath("xl") / target)
        )
    return parts


def _column(reference: str) -> int:
    return column_index_from_string(reference.rstrip("0123456789"))


def _cell(sheet_data, rows: dict, row: int, column: int):
    """The cell at (row, column), created in place when the template has none."""
    row_element = rows.get(row)
    if row_element is None:
        row_element = etree.Element(_tag("row"), r=str(row))
        following = min((r for r in rows if r > row), default=None)
        if following is None:
            sheet_data.append(row_element)
        else:
            rows[following].addprevious(row_element)
        rows[row] = row_element
    reference = f"{get_column_letter(column)}{row}"
    for cell in row_element.findall(_tag("c")):
        if cell.get("r") == reference:
            return cell
        if _column(cell.get("r")) > column:
            new_cell = etree.Element(_tag("c"), r=reference)
            cell.addprevious(new_cell)
            return new_cell
    return etree.SubElement(row_element, _tag("c"), r=reference)


def _set_value(cell, value) -> None:
    """Write a number or a text, keeping the cell's style."""
    if cell.find(_tag("f")) is not None:
        raise ValueError(f"Template cell {cell.get('r')} holds a formula")
    for child in list(cell):
        cell.remove(child)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        cell.attrib.pop("t", None)
        etree.SubElement(cell, _tag("v")).text = str(value)
    else:
        cell.set("t", "inlineStr")
        text = etree.SubElement(etree.SubElement(cell, _tag("is")), _tag("t"))
        text.text = str(value)
        text.set(XML_SPACE, "preserve")


def _drop_cached_results(root) -> bool:
    """Remove formula results computed from the template's values, so that
    every spreadsheet application recomputes them. Returns whether any."""
    dropped = False
    for cell in root.iter(_tag("c")):
        if cell.find(_tag("f")) is not None:
            cached = cell.find(_tag("v"))
            if cached is not None:
                cell.remove(cached)
                dropped = True
            cell.attrib.pop("t", None)
    return dropped


def _recalculate_on_load(workbook_xml: bytes) -> bytes:
    root = etree.fromstring(workbook_xml)
    calculation = root.find(_tag("calcPr"))
    if calculation is None:
        calculation = etree.Element(_tag("calcPr"))
        # Schema order: calcPr follows the last of these (sheets is mandatory).
        preceding = [
            element
            for name in (
                "sheets",
                "functionGroups",
                "externalReferences",
                "definedNames",
            )
            if (element := root.find(_tag(name))) is not None
        ]
        preceding[-1].addnext(calculation)
    calculation.set("fullCalcOnLoad", "1")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def fill_template(path, values: dict[str, dict[tuple[int, int], object]]) -> bytes:
    """The template at `path` with `values[sheet][(row, column)]` written, as
    numbers or texts. Formulas are recomputed when the file is opened."""
    with zipfile.ZipFile(path) as archive:
        parts = _sheet_parts(archive)
        if unknown := set(values) - set(parts):
            raise ValueError(f"Unknown template sheets: {sorted(unknown)}")
        patched = {WORKBOOK: _recalculate_on_load(archive.read(WORKBOOK))}
        for name, part in parts.items():
            root = etree.fromstring(archive.read(part))
            changed = _drop_cached_results(root)
            if cells := values.get(name):
                sheet_data = root.find(_tag("sheetData"))
                rows = {
                    int(row.get("r")): row
                    for row in sheet_data.findall(_tag("row"))
                    if row.get("r")
                }
                for (row, column), value in cells.items():
                    _set_value(_cell(sheet_data, rows, row, column), value)
                changed = True
            if changed:
                patched[part] = etree.tostring(
                    root, xml_declaration=True, encoding="UTF-8", standalone=True
                )
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as result:
            for info in archive.infolist():
                result.writestr(
                    info, patched.get(info.filename) or archive.read(info.filename)
                )
    return buffer.getvalue()
