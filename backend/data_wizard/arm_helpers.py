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

    # Workshop 3 - Stakeholders & Strategic Scenarios
    STAKEHOLDER_CATEGORIES = "3 - Catégories de partie prena"
    STAKEHOLDERS = "3 - Base de parties prenantes"
    STAKEHOLDER_DANGER_LEVELS = "3 - Niveau de danger des parti"
    STRATEGIC_SCENARIOS = "3 - Synthèse des scénarios str"

    # Workshop 4 - Operational Scenarios
    ELEMENTARY_ACTIONS = "4 - Actions élémentaires"

    # Workshop 5 - Risk Treatment Plan (to be added)


# =============================================================================
# Helper functions
# =============================================================================


def normalize_category_name(text: str) -> str:
    """
    Normalize a category name for matching.

    ARM Excel uses French plural forms (e.g., 'Clients') that need to be
    matched to our internal singular forms (e.g., 'client').

    Args:
        text: The raw category name from Excel

    Returns:
        Normalized name (lowercase, trailing 's' stripped)
    """
    if not text:
        return ""

    normalized = text.strip().lower()

    # Strip trailing 's' for plural -> singular conversion
    if normalized.endswith("s") and len(normalized) > 1:
        normalized = normalized[:-1]

    return normalized


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

        # Check if selected (column B: ✓/❒)
        selected_value = row.get("✓/❒") or ""
        is_selected = "✔" in str(selected_value) or "✓" in str(selected_value)

        feared_event = {
            "name": name.strip(),
            "justification": (row.get("Impacts") or "").strip(),
            "gravity": gravity,
            "asset_names": asset_names,
            "is_selected": is_selected,
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
# Workshop 3 Processing
# =============================================================================


def extract_stakeholder_categories(workbook) -> list[dict]:
    """
    Extract stakeholder categories from ARM file.

    These map to Terminology entries for entity.relationship.

    Args:
        workbook: openpyxl Workbook object

    Returns:
        List of dicts with 'name', 'normalized_name', 'description'
    """
    rows = get_sheet_data(workbook, ARMSheets.STAKEHOLDER_CATEGORIES)

    categories = []
    for row in rows:
        name = row.get("Nom")
        if not name:
            continue

        category = {
            "name": name.strip(),
            "normalized_name": normalize_category_name(name),
            "description": (row.get("Description") or "").strip(),
        }
        categories.append(category)

    logger.info(f"Extracted {len(categories)} stakeholder categories from ARM file")
    return categories


def get_stakeholder_danger_data(workbook) -> dict[str, dict]:
    """
    Extract stakeholder danger/assessment data with nested column handling.

    The sheet has:
    - Row 1: Main headers (merged)
    - Row 2: Sub-headers for the assessment columns
    - Row 3+: Data

    Args:
        workbook: openpyxl Workbook object

    Returns:
        Dictionary mapping stakeholder name to assessment data:
        {
            "stakeholder_name": {
                "dependency": int,
                "penetration": int,
                "maturity": int,
                "trust": int,
            }
        }
    """
    sheet_name = ARMSheets.STAKEHOLDER_DANGER_LEVELS
    if sheet_name not in workbook.sheetnames:
        logger.warning(f"Sheet '{sheet_name}' not found in workbook")
        return {}

    sheet = workbook[sheet_name]

    # Get sub-headers from row 2
    sub_headers = [cell.value for cell in sheet[2]]

    # Build a mapping of header names to column indices for flexibility
    header_to_col = {}
    for i, header in enumerate(sub_headers):
        if header:
            header_to_col[header.strip()] = i

    danger_data = {}
    for row in sheet.iter_rows(min_row=3):
        row_values = [cell.value for cell in row]

        # Skip empty rows
        if not any(row_values):
            continue

        # Find stakeholder name - try 'Partie prenante' column or column C (index 2)
        stakeholder_name = None
        if "Partie prenante" in header_to_col:
            stakeholder_name = row_values[header_to_col["Partie prenante"]]
        elif len(row_values) > 2:
            # Fallback to column C (index 2)
            stakeholder_name = row_values[2]

        if not stakeholder_name:
            continue

        assessment = {
            "dependency": 0,
            "penetration": 0,
            "maturity": 1,  # Default to 1 (minimum valid value)
            "trust": 1,  # Default to 1 (minimum valid value)
        }

        # Extract assessment values by header name
        for header, col_idx in header_to_col.items():
            if col_idx >= len(row_values):
                continue
            value = row_values[col_idx]

            if "Dépendance" in header:
                assessment["dependency"] = int(value) if value else 0
            elif "Pénétration" in header:
                assessment["penetration"] = int(value) if value else 0
            elif "Maturité" in header:
                assessment["maturity"] = max(1, int(value) if value else 1)
            elif "Confiance" in header:
                assessment["trust"] = max(1, int(value) if value else 1)

        danger_data[stakeholder_name.strip().lower()] = assessment

    logger.info(f"Extracted danger data for {len(danger_data)} stakeholders")
    return danger_data


def extract_stakeholders(workbook) -> list[dict]:
    """
    Extract stakeholders (entities) from ARM file.

    Args:
        workbook: openpyxl Workbook object

    Returns:
        List of dicts with stakeholder data:
        - name: str (entity name)
        - description: str
        - category: str (normalized category name for matching)
        - risk_origins: list[str] (linked risk origins)
        - current_dependency, current_penetration, current_maturity, current_trust
    """
    rows = get_sheet_data(workbook, ARMSheets.STAKEHOLDERS)

    # Get danger level data for assessment values
    danger_data = get_stakeholder_danger_data(workbook)

    stakeholders = []
    for row in rows:
        name = row.get("Nom")
        if not name:
            continue

        name = name.strip()
        category_raw = row.get("Catégorie") or ""

        # Get assessment data if available
        assessment = danger_data.get(
            name.lower(),
            {
                "dependency": 0,
                "penetration": 0,
                "maturity": 1,
                "trust": 1,
            },
        )

        # Parse risk origins (bullet list)
        risk_origins = parse_bullet_list(row.get("Sources de risque") or "")

        # Check if selected (column B: ✓/❒)
        selected_value = row.get("✓/❒") or ""
        is_selected = "✔" in str(selected_value) or "✓" in str(selected_value)

        stakeholder = {
            "name": name,
            "description": (row.get("Description") or "").strip(),
            "category": normalize_category_name(category_raw),
            "category_raw": category_raw.strip(),
            "risk_origins": risk_origins,
            "is_selected": is_selected,
            "current_dependency": assessment["dependency"],
            "current_penetration": assessment["penetration"],
            "current_maturity": assessment["maturity"],
            "current_trust": assessment["trust"],
        }
        stakeholders.append(stakeholder)

    logger.info(f"Extracted {len(stakeholders)} stakeholders from ARM file")
    return stakeholders


def extract_strategic_scenarios(workbook) -> list[dict]:
    """
    Extract strategic scenarios from ARM file.

    The sheet has:
    - Row 1: Main headers (merged)
    - Row 2: Sub-headers
    - Row 3+: Data

    Column layout (0-indexed):
    - Columns A-D (0-3): Scenario info (Nom, Abrév.)
    - Columns E-F (4-5): RoTo reference (Source de risque, Objectif visé)
    - Columns H-I (7-8): Attack path (Réf., Nom)

    Args:
        workbook: openpyxl Workbook object

    Returns:
        List of dicts with strategic scenario data
    """
    sheet_name = ARMSheets.STRATEGIC_SCENARIOS
    if sheet_name not in workbook.sheetnames:
        logger.warning(f"Sheet '{sheet_name}' not found in workbook")
        return []

    sheet = workbook[sheet_name]

    # Get headers from row 1 and sub-headers from row 2
    headers_row1 = [cell.value for cell in sheet[1]]
    sub_headers = [cell.value for cell in sheet[2]]

    # Find column indices by scanning both header rows
    # Column layout based on actual data:
    # - Column C (index 2): Scenario name (under merged header in row 1)
    # - Column E (index 4): Source de risque
    # - Column F (index 5): Objectif visé
    # - Column H (index 7): Attack path Réf.
    # - Column I (index 8): Attack path Nom
    scenario_name_col = None
    scenario_ref_col = None
    risk_origin_col = None
    target_objective_col = None
    attack_path_ref_col = None
    attack_path_name_col = None

    for i, header in enumerate(sub_headers):
        if not header:
            continue
        header_clean = header.strip()

        if header_clean == "Source de risque":
            risk_origin_col = i
        elif header_clean == "Objectif visé":
            target_objective_col = i
        elif header_clean == "Réf.":
            attack_path_ref_col = i
        elif header_clean == "Nom":
            attack_path_name_col = i

    # Check row 1 for scenario name column (often under a merged "Scénario" header)
    for i, header in enumerate(headers_row1):
        if header and "Nom" in str(header):
            scenario_name_col = i
            break
        elif header and "Abrév" in str(header):
            scenario_ref_col = i

    # Fallback: scenario name is typically in column C (index 2) based on observed data
    if scenario_name_col is None:
        scenario_name_col = 2

    scenarios = []
    for row in sheet.iter_rows(min_row=3):
        row_values = [cell.value for cell in row]

        # Skip empty rows
        if not any(row_values):
            continue

        def get_val(col_idx):
            if col_idx is not None and col_idx < len(row_values):
                return row_values[col_idx]
            return None

        scenario_name = get_val(scenario_name_col)
        if not scenario_name:
            continue

        scenario = {
            "name": str(scenario_name).strip(),
            "ref_id": (str(get_val(scenario_ref_col) or "")).strip(),
            "risk_origin": (str(get_val(risk_origin_col) or "")).strip(),
            "target_objective": (str(get_val(target_objective_col) or "")).strip(),
            "attack_path_ref_id": (str(get_val(attack_path_ref_col) or "")).strip(),
            "attack_path_name": (str(get_val(attack_path_name_col) or "")).strip(),
        }
        scenarios.append(scenario)

    logger.info(f"Extracted {len(scenarios)} strategic scenarios from ARM file")
    return scenarios


# =============================================================================
# Workshop 4 Processing
# =============================================================================


def extract_elementary_actions(workbook) -> list[dict]:
    """
    Extract elementary actions from ARM file.

    Args:
        workbook: openpyxl Workbook object

    Returns:
        List of dicts with elementary action data:
        - name: str
        - description: str
        - ref_id: str
    """
    rows = get_sheet_data(workbook, ARMSheets.ELEMENTARY_ACTIONS)

    elementary_actions = []
    for row in rows:
        name = row.get("Nom")
        if not name:
            continue

        elementary_action = {
            "name": name.strip(),
            "description": (row.get("Description") or "").strip(),
            "ref_id": (row.get("Abrév.") or "").strip(),
        }
        elementary_actions.append(elementary_action)

    logger.info(f"Extracted {len(elementary_actions)} elementary actions from ARM file")
    return elementary_actions


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

    # Extract Workshop 3 data
    result["stakeholder_categories"] = extract_stakeholder_categories(workbook)
    result["stakeholders"] = extract_stakeholders(workbook)
    result["strategic_scenarios"] = extract_strategic_scenarios(workbook)

    # Extract Workshop 4 data
    result["elementary_actions"] = extract_elementary_actions(workbook)

    logger.info(
        f"Extracted from ARM file: "
        f"{len(result['primary_assets'])} primary assets, "
        f"{len(result['supporting_assets'])} supporting assets, "
        f"{len(result['feared_events'])} feared events, "
        f"{len(result['applied_controls'])} applied controls, "
        f"{len(result['roto_couples'])} RoTo couples, "
        f"{len(result['stakeholders'])} stakeholders, "
        f"{len(result['strategic_scenarios'])} strategic scenarios, "
        f"{len(result['elementary_actions'])} elementary actions"
    )

    return result
