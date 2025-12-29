"""
ARM Format Helper for EBIOS RM Study Import

This module handles the import of EBIOS RM studies from ARM Excel format.
ARM exports studies with 91 sheets organized by workshop.
"""

import logging
from io import BytesIO

from openpyxl import load_workbook

logger = logging.getLogger(__name__)


# =============================================================================
# Sheet name constants
# =============================================================================


class ARMSheets:
    """ARM Excel sheet names organized by workshop."""

    # Workshop 1 - Scope & Security Baseline
    BUSINESS_VALUES = "1 - Base de valeurs métier"
    MISSIONS = "1 - Base de missions"
    FEARED_EVENTS = "1 - Base d'évènements redoutés"
    SUPPORTING_ASSETS = "1 - Biens supports"
    IMPACT_LEVEL_SCALE = "1 - Échelle de niveau d'impact"
    COMPLEMENTARY_MEASURES = "1 - Mesures complémentaires"

    # Workshop 2 - Risk Origins
    ROTO_COUPLES = "2 - Base de couples SR OV"

    # Workshop 3 - Strategic Scenarios (to be added)
    # Workshop 4 - Operational Scenarios (to be added)
    # Workshop 5 - Risk Treatment Plan (to be added)


# =============================================================================
# Helper functions
# =============================================================================


def parse_plus_signs(text: str) -> int:
    """
    Parse '+' signs from ARM Excel format to numeric value.

    ARM uses '+', '++', '+++', '++++' to represent levels 1-4.
    Empty or invalid values return 0 (undefined).

    Args:
        text: The raw text from the Excel cell

    Returns:
        Numeric value (0-4)
    """
    if not text:
        return 0

    text = str(text).strip()
    # Count the '+' signs
    plus_count = text.count("+")

    # Validate it's only '+' characters
    if plus_count > 0 and text == "+" * plus_count:
        return min(plus_count, 4)  # Cap at 4

    return 0


def parse_bullet_list(text: str) -> list[str]:
    """
    Parse a bullet-pointed list from ARM Excel format.

    ARM uses '•' as bullet points with '_x000D_\\n' or '\\n' as line separators.

    Args:
        text: The raw text from the Excel cell

    Returns:
        List of cleaned items without bullet points
    """
    if not text:
        return []

    # Replace ARM line breaks with standard newlines
    text = text.replace("_x000D_\n", "\n").replace("_x000D_", "\n")

    items = []
    for line in text.split("\n"):
        line = line.strip()
        # Remove bullet point prefix
        if line.startswith("•"):
            line = line[1:].strip()
        if line:
            items.append(line)

    return items


def get_sheet_data(workbook, sheet_name: str, skip_header_rows: int = 2) -> list[dict]:
    """
    Extract data rows from an ARM Excel sheet.

    ARM sheets typically have:
    - Row 1: Main headers
    - Row 2: Sub-headers (for merged columns)
    - Row 3+: Data

    Args:
        workbook: openpyxl Workbook object
        sheet_name: Name of the sheet to read
        skip_header_rows: Number of header rows to skip (default 2)

    Returns:
        List of dictionaries with column name -> value mapping
    """
    if sheet_name not in workbook.sheetnames:
        logger.warning(f"Sheet '{sheet_name}' not found in workbook")
        return []

    sheet = workbook[sheet_name]

    # Get headers from first row
    headers = [cell.value for cell in sheet[1]]

    rows = []
    for row_idx, row in enumerate(
        sheet.iter_rows(min_row=skip_header_rows + 1), start=skip_header_rows + 1
    ):
        row_data = {}
        for i, cell in enumerate(row):
            if i < len(headers) and headers[i]:
                row_data[headers[i]] = cell.value

        # Skip empty rows
        if any(v for v in row_data.values() if v):
            rows.append(row_data)

    return rows


# =============================================================================
# Workshop 1 Processing
# =============================================================================


def build_gravity_scale_mapping(workbook) -> dict[str, int]:
    """
    Build a mapping from gravity level names to numeric values.

    Reads from '1 - Échelle de niveau d'impact' sheet.
    Maps 'Niveau de gravité' -> 'Niveau' - 1 (CISO Assistant is 0-indexed).

    Args:
        workbook: openpyxl Workbook object

    Returns:
        Dictionary mapping gravity names (lowercase) to numeric values
    """
    mapping = {}

    rows = get_sheet_data(workbook, ARMSheets.IMPACT_LEVEL_SCALE)

    for row in rows:
        gravity_name = row.get("Niveau de gravité")
        niveau = row.get("Niveau")

        if gravity_name and niveau is not None:
            try:
                # CISO Assistant is 0-indexed, ARM Excel is 1-indexed
                numeric_value = int(niveau) - 1
                mapping[gravity_name.lower().strip()] = numeric_value
                logger.debug(f"Gravity mapping: '{gravity_name}' -> {numeric_value}")
            except (ValueError, TypeError):
                logger.warning(f"Invalid Niveau value: {niveau}")

    return mapping


def extract_missions(workbook) -> str:
    """
    Extract missions from the ARM file to use as study description.

    Args:
        workbook: openpyxl Workbook object

    Returns:
        String with all missions joined by newlines
    """
    rows = get_sheet_data(workbook, ARMSheets.MISSIONS)

    missions = []
    for row in rows:
        mission = row.get("Mission")
        if mission:
            missions.append(mission.strip())

    return "\n".join(missions)


def extract_primary_assets(workbook) -> list[dict]:
    """
    Extract primary assets from 'Base de valeurs métier' sheet.

    Args:
        workbook: openpyxl Workbook object

    Returns:
        List of dicts with 'name', 'description', 'type', 'supporting_assets'
    """
    rows = get_sheet_data(workbook, ARMSheets.BUSINESS_VALUES)

    assets = []
    for row in rows:
        name = row.get("Nom")
        if not name:
            continue

        asset = {
            "name": name.strip(),
            "description": (row.get("Description") or "").strip(),
            "type": "PR",  # Primary
            "supporting_asset_names": parse_bullet_list(
                row.get("Biens supports") or ""
            ),
        }
        assets.append(asset)

    return assets


def extract_supporting_assets(workbook) -> list[dict]:
    """
    Extract supporting assets from 'Biens supports' sheet.

    Args:
        workbook: openpyxl Workbook object

    Returns:
        List of dicts with 'name', 'description', 'type', 'parent_name'
    """
    rows = get_sheet_data(workbook, ARMSheets.SUPPORTING_ASSETS)

    assets = []
    for row in rows:
        name = row.get("Nom")
        if not name:
            continue

        # Get parent asset name if specified
        parent_name = (row.get("Bien support parent") or "").strip()

        asset = {
            "name": name.strip(),
            "description": (row.get("Description") or "").strip(),
            "type": "SP",  # Supporting
            "parent_name": parent_name if parent_name else None,
        }
        assets.append(asset)

    return assets


def extract_feared_events(workbook, gravity_mapping: dict[str, int]) -> list[dict]:
    """
    Extract feared events from 'Base d'évènements redoutés' sheet.

    Args:
        workbook: openpyxl Workbook object
        gravity_mapping: Dictionary mapping gravity names to numeric values

    Returns:
        List of dicts with feared event data
    """
    rows = get_sheet_data(workbook, ARMSheets.FEARED_EVENTS)

    feared_events = []
    for row in rows:
        name = row.get("Évènement redouté")
        if not name:
            continue

        # Parse gravity
        gravity_text = row.get("Gravité retenue") or ""
        gravity = gravity_mapping.get(gravity_text.lower().strip(), -1)

        # Parse linked assets
        asset_names = parse_bullet_list(row.get("Valeurs métier") or "")

        feared_event = {
            "name": name.strip(),
            "justification": (row.get("Impacts") or "").strip(),
            "gravity": gravity,
            "asset_names": asset_names,
        }
        feared_events.append(feared_event)

    return feared_events


def extract_applied_controls(workbook) -> list[dict]:
    """
    Extract applied controls from 'Mesures complémentaires' sheet.

    Args:
        workbook: openpyxl Workbook object

    Returns:
        List of dicts with 'name', 'description', 'ref_id'
    """
    rows = get_sheet_data(workbook, ARMSheets.COMPLEMENTARY_MEASURES)

    controls = []
    for row in rows:
        name = row.get("Nom")
        if not name:
            continue

        control = {
            "name": name.strip(),
            "description": (row.get("Description") or "").strip(),
            "ref_id": (row.get("Réf.") or "").strip(),
        }
        controls.append(control)

    return controls


# =============================================================================
# Workshop 2 Processing
# =============================================================================


def get_roto_sheet_data(workbook) -> list[dict]:
    """
    Extract data from the RoTo couples sheet with special handling for merged headers.

    The RoTo sheet has:
    - Row 1: Main headers (some merged)
    - Row 2: Sub-headers
    - Row 3+: Data

    Sub-header columns:
    - Source de risque, Objectif visé (under Identification)
    - Motivation, Ressources, Activité (under Cotation)
    - Pertinence (under Évaluation de la pertinence)
    - Retenu (under Paramètres de la justification)
    - Justification

    Args:
        workbook: openpyxl Workbook object

    Returns:
        List of dictionaries with sub-header -> value mapping
    """
    sheet_name = ARMSheets.ROTO_COUPLES
    if sheet_name not in workbook.sheetnames:
        logger.warning(f"Sheet '{sheet_name}' not found in workbook")
        return []

    sheet = workbook[sheet_name]

    # Get sub-headers from row 2
    sub_headers = [cell.value for cell in sheet[2]]

    rows = []
    for row_idx, row in enumerate(sheet.iter_rows(min_row=3), start=3):
        row_data = {}
        for i, cell in enumerate(row):
            if i < len(sub_headers) and sub_headers[i]:
                row_data[sub_headers[i]] = cell.value

        # Skip empty rows
        if any(v for v in row_data.values() if v):
            rows.append(row_data)

    return rows


def extract_roto_couples(workbook) -> list[dict]:
    """
    Extract RoTo (Risk Origin / Target Objective) couples from ARM file.

    Args:
        workbook: openpyxl Workbook object

    Returns:
        List of dicts with RoTo couple data:
        - risk_origin: str (Source de risque)
        - target_objective: str (Objectif visé)
        - motivation: int (0-4)
        - resources: int (0-4)
        - activity: int (0-4)
        - is_selected: bool
        - justification: str
    """
    rows = get_roto_sheet_data(workbook)

    roto_couples = []
    for row in rows:
        risk_origin = row.get("Source de risque")
        target_objective = row.get("Objectif visé")

        if not risk_origin or not target_objective:
            continue

        # Parse '+' signs to numeric values
        motivation = parse_plus_signs(row.get("Motivation") or "")
        resources = parse_plus_signs(row.get("Ressources") or "")
        activity = parse_plus_signs(row.get("Activité") or "")

        # Check if selected (✔ or similar)
        retenu = row.get("Retenu") or ""
        is_selected = "✔" in str(retenu) or "✓" in str(retenu)

        justification = (row.get("Justification") or "").strip()

        roto = {
            "risk_origin": risk_origin.strip(),
            "target_objective": target_objective.strip(),
            "motivation": motivation,
            "resources": resources,
            "activity": activity,
            "is_selected": is_selected,
            "justification": justification,
        }
        roto_couples.append(roto)

    logger.info(f"Extracted {len(roto_couples)} RoTo couples from ARM file")
    return roto_couples


# =============================================================================
# Main processing function
# =============================================================================


def process_arm_file(file_content: bytes) -> dict:
    """
    Process an ARM Excel file and extract all relevant data.

    Args:
        file_content: Raw bytes of the Excel file

    Returns:
        Dictionary with extracted data organized by type
    """
    workbook = load_workbook(BytesIO(file_content), data_only=True)

    # Build gravity mapping first (needed for feared events)
    gravity_mapping = build_gravity_scale_mapping(workbook)
    logger.info(
        f"Built gravity mapping with {len(gravity_mapping)} levels: {gravity_mapping}"
    )

    # Extract Workshop 1 data
    result = {
        "study_description": extract_missions(workbook),
        "primary_assets": extract_primary_assets(workbook),
        "supporting_assets": extract_supporting_assets(workbook),
        "feared_events": extract_feared_events(workbook, gravity_mapping),
        "applied_controls": extract_applied_controls(workbook),
        "gravity_mapping": gravity_mapping,
    }

    # Extract Workshop 2 data
    result["roto_couples"] = extract_roto_couples(workbook)

    logger.info(
        f"Extracted from ARM file: "
        f"{len(result['primary_assets'])} primary assets, "
        f"{len(result['supporting_assets'])} supporting assets, "
        f"{len(result['feared_events'])} feared events, "
        f"{len(result['applied_controls'])} applied controls, "
        f"{len(result['roto_couples'])} RoTo couples"
    )

    return result
