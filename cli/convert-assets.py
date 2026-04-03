#!/usr/bin/env python3
"""convert-assets.py
Convert "asset test.csv" format to CISO Assistant import format.

Usage:
    python convert-assets.py --input "e:/asset test.csv" --output assets_import.csv
    python convert-assets.py --input "e:/asset test.csv" --output assets_import.csv --encoding cp1252

Field mapping from source to CISO Assistant:
    Name                → name + ref_id
    Description         → description
    Class               → label (normalized: Business_Function, DIGITAL, etc.)
    ID                  → ref_id (only when equals Name for BF/EA)
    Domain              → domain (fallback)
    Type                → domain (primary: Infrastructure, Compute, Network, etc.)
    Dependencies_upstream  → parent_assets (Essential Assets, BFs)
    Dependencies_downstream → parent_assets (Physical/Logical/Network assets)
    Confidentiality / Integrity / Availability / Proof / Authenticity / Privacy / Safety
                        → security_objectives (High=3, Medium=2, Low=1)
    RTO_hours/min/sec + RPO_hours/min/sec + MTD_hours/min/sec
                        → disaster_recovery_objectives ("rto: 24h, rpo: 24h, mtd: 96h")
    Is_business_function → label BF added (yes -> prepend BF label)
    Link                → reference_link
    Observation         → observation
    Homologation_status → localisation (contains physical location codes: STBY, B11/1/57, etc.)
    Labels              → labels

NOTE: 'domain' values from source (Infrastructure, Compute, Network, Business, etc.)
must already exist as Folders in CISO Assistant before import.
"""

import csv
import sys
import argparse
import re
from pathlib import Path


# Map text severity to integer (CISO Assistant uses 0-4 scale)
SEVERITY_MAP: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "very high": 4,
    "critical": 4,
}

# Security objective columns in source CSV (in order)
SEC_OBJ_COLS = [
    "Confidentiality",
    "Integrity",
    "Availability",
    "Proof",
    "Authenticity",
    "Privacy",
    "Safety",
]

# RTO / RPO / MTD column groups (key, hours_col, minutes_col, seconds_col)
TIME_COLS = [
    ("rto", "RTO_hours", "RTO_minutes", "RTO_seconds"),
    ("rpo", "RPO_hours", "RPO_minutes", "RPO_seconds"),
    ("mtd", "MTD_hours", "MTD_minutes", "MTD_seconds"),
]

# Asset classes that map to Primary (PR) in CISO Assistant
PRIMARY_CLASSES = {"business function", "essential asset", "primary asset"}

# Output columns (in order)
OUT_COLS = [
    "ref_id",
    "name",
    "description",
    "type",
    "domain",
    "localisation",
    "observation",
    "reference_link",
    "security_objectives",
    "disaster_recovery_objectives",
    "parent_assets",
    "labels",
]


def detect_delimiter(lines: list[str]) -> str:
    """Detect CSV delimiter from a short sample, fallback to comma."""
    sample = "\n".join(lines[:30])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ","


def sanitize_csv_line(line: str) -> str:
    """Repair malformed closing quotes like '"value"" ,' from legacy exports."""
    return re.sub(r'"([^"\r\n]*)""(?=,|;|\t|\||$)', r'"\1"', line)


def map_severity(value: str) -> int | None:
    if not value or not value.strip():
        return None
    return SEVERITY_MAP.get(value.strip().lower())


def build_security_objectives(row: dict) -> str:
    parts = []
    for col in SEC_OBJ_COLS:
        num = map_severity(row.get(col, ""))
        if num is not None:
            parts.append(f"{col.lower()}: {num}")
    return ", ".join(parts)


def build_time_str(h: str, m: str, s: str) -> str | None:
    try:
        hours = int(h) if h and h.strip() else 0
        minutes = int(m) if m and m.strip() else 0
    except ValueError:
        return None
    # Normalize: convert minutes >= 60 to hours
    hours += minutes // 60
    minutes = minutes % 60
    if hours == 0 and minutes == 0:
        return None
    if hours > 0 and minutes > 0:
        return f"{hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h"
    return f"{minutes}m"


def build_disaster_recovery_objectives(row: dict) -> str:
    parts = []
    for key, h_col, m_col, s_col in TIME_COLS:
        val = build_time_str(row.get(h_col, ""), row.get(m_col, ""), row.get(s_col, ""))
        if val:
            parts.append(f"{key}: {val}")
    return ", ".join(parts)


def determine_asset_type(row: dict) -> str:
    """Return PR (primary) or SP (support) based on Class field."""
    asset_class = (row.get("Class") or "").strip().lower()
    return "PR" if asset_class in PRIMARY_CLASSES else "SP"


def is_valid_refids(val: str) -> bool:
    """Return True if value looks like asset ref_ids (no spaces, short tokens)."""
    if not val:
        return False
    tokens = [t.strip() for t in val.replace(";", "|").split("|")]
    return all(t and " " not in t and len(t) <= 60 for t in tokens)


def build_parent_assets(row: dict) -> str:
    """
    Essential assets reference BF ref_ids in Dependencies_upstream.
    Physical/network assets reference logical asset ref_ids in Dependencies_downstream.
    The heuristic: ref_ids have no spaces (unlike descriptions like 'COMPUTER SYSTEM').
    """
    upstream = (row.get("Dependencies_upstream") or "").strip()
    downstream = (row.get("Dependencies_downstream") or "").strip()

    if is_valid_refids(upstream):
        return upstream.replace(";", "|")
    if is_valid_refids(downstream):
        return downstream.replace(";", "|")
    return ""


def build_labels(row: dict) -> str:
    """Combine source Labels column + Class + Type as normalized labels."""
    parts = []

    # Source Labels column (may be empty)
    src = (row.get("Labels") or "").strip()
    if src:
        parts.extend(t.strip() for t in src.replace(";", "|").split("|") if t.strip())

    # Add Class as label (spaces → underscores)
    asset_class = (row.get("Class") or "").strip()
    if asset_class:
        normalized = asset_class.replace(" ", "_")
        if normalized not in parts:
            parts.append(normalized)

    # Add Type as label (spaces → underscores) — equipment type / classification code
    src_type = (row.get("Type") or "").strip()
    if src_type:
        normalized_type = src_type.replace(" ", "_")
        if normalized_type not in parts:
            parts.append(normalized_type)

    # Add Domain code as label if it was rejected as a folder (numeric code like SDNSCD114)
    import re as _re
    src_domain = (row.get("Domain") or "").strip()
    if src_domain and _re.search(r"\d{3,}", src_domain):
        domain_label = src_domain.replace(" ", "_").replace("/", "_")
        if domain_label not in parts:
            parts.append(domain_label)

    return "|".join(parts)


def determine_domain(row: dict) -> str:
    """
    Use source 'Domain' column as CISO Assistant folder only when it looks like
    a meaningful folder name (no digits-heavy codes like SDNSCD114).
    Known valid values: Business, Essential, Infrastructure, Global, etc.
    Unknown codes are stored as labels instead and domain defaults to Global.
    """
    src_domain = (row.get("Domain") or "").strip()
    if not src_domain:
        return "Global"
    # Accept values that are mostly letters/spaces (no long digit sequences)
    import re as _re
    if _re.search(r"\d{3,}", src_domain):
        # Looks like a code (e.g. SDNSCD114, 50/125-OM3) — not a valid folder name
        return "Global"
    return src_domain


def determine_ref_id(row: dict) -> str:
    """
    For Business Functions and Essential Assets: ID == Name → use it.
    For physical assets: ID column contains a classification string ('Physical Asset', etc.)
      → fall back to Name as ref_id.
    Limit ref_id to 100 chars max (CISO Assistant constraint).
    """
    name = (row.get("Name") or "").strip()
    src_id = (row.get("ID") or "").strip()
    # Use src_id only when it has no spaces (clean code like VM-C2-01, YNAB106830)
    if src_id and " " not in src_id:
        ref_id = src_id
    else:
        ref_id = name
    # Limit to 100 chars as per CISO Assistant validation
    return ref_id[:100]


def convert(input_path: Path, output_path: Path, encoding: str, override_domain: str | None) -> None:
    # Auto-detect encoding. Try common encodings in order.
    # cp437/cp850 = DOS/IBM OEM (common for CSV exports from legacy tools)
    if encoding == "auto":
        for enc in ("utf-8-sig", "utf-16", "utf-8", "cp437", "cp850", "cp1252", "latin-1"):
            try:
                with open(input_path, encoding=enc, newline="") as f:
                    sample = f.read(4096)
                # Sanity check: result should have high ratio of printable chars
                # and specifically should NOT contain replacement chars (which cp1252 lets through)
                printable_ratio = sum(1 for c in sample if c.isprintable() or c in "\r\n\t") / max(len(sample), 1)
                # For cp437/cp850, check that typical accented chars are in acceptable range
                if printable_ratio > 0.95:
                    encoding = enc
                    print(f"Auto-detected encoding: {enc}")
                    break
            except (UnicodeDecodeError, UnicodeError, LookupError):
                continue
        else:
            encoding = "latin-1"
            print(f"Falling back to encoding: {encoding}")

    try:
        with open(input_path, encoding=encoding, newline="", errors="replace") as f:
            raw_lines = f.read().splitlines()
    except FileNotFoundError:
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if not raw_lines:
        print("Warning: source file is empty.", file=sys.stderr)
        sys.exit(1)

    delimiter = detect_delimiter(raw_lines)

    # Parse row-by-row so malformed quotes on one line never corrupt the next lines.
    try:
        headers = next(csv.reader([raw_lines[0]], delimiter=delimiter))
    except (csv.Error, StopIteration):
        print("Error: unable to parse CSV header.", file=sys.stderr)
        sys.exit(1)

    rows = []
    parse_errors = 0
    for line_no, raw_line in enumerate(raw_lines[1:], start=2):
        if not raw_line.strip():
            continue

        fixed_line = sanitize_csv_line(raw_line)
        try:
            values = next(csv.reader([fixed_line], delimiter=delimiter))
        except csv.Error:
            parse_errors += 1
            continue

        if len(values) < len(headers):
            values.extend([""] * (len(headers) - len(values)))
        elif len(values) > len(headers):
            # Preserve extra commas by folding the overflow into the last column.
            values = values[:len(headers) - 1] + [delimiter.join(values[len(headers) - 1:])]

        rows.append(dict(zip(headers, values)))

    if not rows:
        print("Warning: source file is empty or has no data rows.", file=sys.stderr)
        sys.exit(1)

    # Show detected columns for debugging
    first_row = rows[0]
    print(f"Detected delimiter: {repr(delimiter)}")
    print(f"Detected columns: {list(first_row.keys())}")
    print(f"Processing {len(rows)} source rows...")
    if parse_errors:
        print(f"Skipped {parse_errors} unparsable rows due to malformed CSV quoting.")

    out_rows = []
    skipped = 0

    for i, row in enumerate(rows, start=2):  # start=2 (row 1 is header)
        name = (row.get("Name") or "").strip()
        if not name:
            skipped += 1
            continue

        ref_id = determine_ref_id(row)
        description = (row.get("Description") or "").strip()
        asset_type = determine_asset_type(row)
        domain = override_domain if override_domain else determine_domain(row)

        # Source 'Homologation_status' column contains physical location codes
        # (STBY, B11/1/57, INV-CEM, R119, etc.) → mapped to localisation
        localisation = (row.get("Homologation_status") or "").strip()

        observation = (row.get("Observation") or "").strip()
        reference_link = (row.get("Link") or "").strip()

        security_objectives = build_security_objectives(row)
        disaster_recovery_objectives = build_disaster_recovery_objectives(row)
        parent_assets = build_parent_assets(row)
        labels = build_labels(row)

        out_rows.append({
            "ref_id": ref_id,
            "name": name,
            "description": description,
            "type": asset_type,
            "domain": domain,
            "localisation": localisation,
            "observation": observation,
            "reference_link": reference_link,
            "security_objectives": security_objectives,
            "disaster_recovery_objectives": disaster_recovery_objectives,
            "parent_assets": parent_assets,
            "labels": labels,
        })

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_COLS)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"\nDone: {len(out_rows)} assets written to {output_path}")
    if skipped:
        print(f"Skipped {skipped} empty rows.")

    # Summary of domains found (must exist as Folders in CISO Assistant)
    domains = sorted({r["domain"] for r in out_rows if r["domain"]})
    print(f"\nDomains found (must exist as Folders in CISO Assistant before import):")
    for d in domains:
        print(f"  - {d}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert asset test CSV to CISO Assistant import format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Source CSV file path (e.g. 'e:/asset test.csv')",
    )
    parser.add_argument(
        "--output", "-o", default="assets_import.csv",
        help="Output CSV file (default: assets_import.csv)",
    )
    parser.add_argument(
        "--encoding", "-e", default="auto",
        help="Source file encoding (default: auto-detect). Try cp1252, utf-8-sig, or latin-1.",
    )
    parser.add_argument(
        "--override-domain", "-d", default=None, dest="override_domain",
        help="Force all assets into a single folder (e.g. 'Global'). Overrides source Domain column.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    convert(input_path, output_path, args.encoding, args.override_domain)


if __name__ == "__main__":
    main()
