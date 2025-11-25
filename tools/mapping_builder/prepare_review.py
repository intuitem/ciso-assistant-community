#!/usr/bin/env python3
"""
Prepare mapping review from CSV output.
Generates Excel and HTML formats for human review.
"""

import argparse
import pandas as pd
from pathlib import Path
from openpyxl.styles import Alignment


def favor_equals_filter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter DataFrame to favor equal relationships.
    For each source_ref_id, keep only 'equal' relationships if they exist,
    otherwise keep all relationships for that source.
    """
    filtered_rows = []

    for source_id in df["source_ref_id"].unique():
        source_matches = df[df["source_ref_id"] == source_id]
        equal_matches = source_matches[source_matches["relationship"] == "equal"]

        if len(equal_matches) > 0:
            # Has equal matches, keep only those
            filtered_rows.append(equal_matches)
        else:
            # No equal matches, keep all matches for this source
            filtered_rows.append(source_matches)

    return pd.concat(filtered_rows, ignore_index=True)


def create_excel_review(input_csv: str, output_excel: str, favor_equals: bool = False):
    """Create Excel file for mapping review."""
    df = pd.read_csv(input_csv)

    if favor_equals:
        original_count = len(df)
        df = favor_equals_filter(df)
        print(
            f"Favor-equals mode: filtered from {original_count} to {len(df)} mappings"
        )

    # Select and rename columns for review
    review_df = pd.DataFrame(
        {
            "source_node_id": df["source_ref_id"],
            "target_node_id": df["target_ref_id"],
            "relationship": df["relationship"],
            "source_description": df["source_full_sentence"],
            "target_description": df["target_full_sentence"],
        }
    )

    # Create Excel file with formatting
    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        review_df.to_excel(writer, index=False, sheet_name="Mapping Review")

        # Get the worksheet
        worksheet = writer.sheets["Mapping Review"]

        # Set column widths
        worksheet.column_dimensions["A"].width = 15  # source_node_id
        worksheet.column_dimensions["B"].width = 15  # target_node_id
        worksheet.column_dimensions["C"].width = 15  # relationship
        worksheet.column_dimensions["D"].width = 50  # source_description
        worksheet.column_dimensions["E"].width = 50  # target_description

        # Apply text wrapping to all cells
        wrap_alignment = Alignment(wrap_text=True, vertical="top")
        for row in worksheet.iter_rows():
            for cell in row:
                cell.alignment = wrap_alignment

    print(f"Excel review file created: {output_excel}")


def create_html_review(input_csv: str, output_html: str, favor_equals: bool = False):
    """Create standalone HTML file for mapping review."""
    df = pd.read_csv(input_csv)

    if favor_equals:
        original_count = len(df)
        df = favor_equals_filter(df)
        print(
            f"Favor-equals mode: filtered from {original_count} to {len(df)} mappings"
        )

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mapping Review</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 30px;
        }}

        h1 {{
            color: #2c3e50;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 3px solid #3498db;
        }}

        .stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
            padding: 15px;
            background: #ecf0f1;
            border-radius: 5px;
        }}

        .stat-item {{
            flex: 1;
            text-align: center;
        }}

        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }}

        .stat-label {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}

        thead {{
            background: #34495e;
            color: white;
        }}

        th {{
            padding: 12px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
            background: #34495e;
        }}

        td {{
            padding: 12px;
            border-bottom: 1px solid #ddd;
            vertical-align: top;
        }}

        tbody tr:hover {{
            background: #f8f9fa;
        }}

        tbody tr.reviewed {{
            background: #d4edda;
        }}

        .ref-id {{
            font-family: 'Courier New', monospace;
            font-weight: 600;
            color: #2c3e50;
            white-space: nowrap;
        }}

        .description {{
            font-size: 0.9em;
            line-height: 1.5;
        }}

        .relationship {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .relationship.equal {{
            background: #27ae60;
            color: white;
        }}

        .relationship.intersect {{
            background: #3498db;
            color: white;
        }}

        .relationship.subset {{
            background: #f39c12;
            color: white;
        }}

        .relationship.superset {{
            background: #e67e22;
            color: white;
        }}

        .relationship.no_relationship {{
            background: #95a5a6;
            color: white;
        }}

        .checkbox-cell {{
            text-align: center;
        }}

        input[type="checkbox"] {{
            width: 20px;
            height: 20px;
            cursor: pointer;
        }}

        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #ecf0f1;
            border-radius: 5px;
            overflow: hidden;
            margin-bottom: 20px;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #3498db, #2ecc71);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Mapping Review</h1>

        <div class="progress-bar">
            <div class="progress-fill" id="progressBar">0%</div>
        </div>

        <div class="stats">
            <div class="stat-item">
                <div class="stat-value" id="totalMappings">{total_mappings}</div>
                <div class="stat-label">Total Mappings</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="reviewedCount">0</div>
                <div class="stat-label">Reviewed</div>
            </div>
            <div class="stat-item">
                <div class="stat-value" id="remainingCount">{total_mappings}</div>
                <div class="stat-label">Remaining</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Source Ref</th>
                    <th>Source Description</th>
                    <th>Relationship</th>
                    <th>Target Ref</th>
                    <th>Target Description</th>
                    <th>Reviewed</th>
                </tr>
            </thead>
            <tbody>
{table_rows}
            </tbody>
        </table>
    </div>

    <script>
        function updateStats() {{{{
            const checkboxes = document.querySelectorAll('input[type="checkbox"]');
            const total = checkboxes.length;
            const reviewed = Array.from(checkboxes).filter(cb => cb.checked).length;
            const remaining = total - reviewed;
            const percentage = total > 0 ? Math.round((reviewed / total) * 100) : 0;

            document.getElementById('reviewedCount').textContent = reviewed;
            document.getElementById('remainingCount').textContent = remaining;
            document.getElementById('progressBar').style.width = percentage + '%';
            document.getElementById('progressBar').textContent = percentage + '%';

            // Update row styling
            checkboxes.forEach(cb => {{{{
                const row = cb.closest('tr');
                if (cb.checked) {{{{
                    row.classList.add('reviewed');
                }}}} else {{{{
                    row.classList.remove('reviewed');
                }}}}
            }}}});

            // Save state to localStorage
            saveState();
        }}}}

        function saveState() {{{{
            const checkboxes = document.querySelectorAll('input[type="checkbox"]');
            const state = Array.from(checkboxes).map(cb => cb.checked);
            localStorage.setItem('mappingReviewState', JSON.stringify(state));
        }}}}

        function loadState() {{{{
            const saved = localStorage.getItem('mappingReviewState');
            if (saved) {{{{
                const state = JSON.parse(saved);
                const checkboxes = document.querySelectorAll('input[type="checkbox"]');
                state.forEach((checked, index) => {{{{
                    if (checkboxes[index]) {{{{
                        checkboxes[index].checked = checked;
                    }}}}
                }}}});
                updateStats();
            }}}}
        }}}}

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {{{{
            const checkboxes = document.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(cb => {{{{
                cb.addEventListener('change', updateStats);
            }}}});

            loadState();
            updateStats();
        }}}});
    </script>
</body>
</html>"""

    # Build table rows
    rows = []
    for idx, row in df.iterrows():
        relationship_class = row["relationship"].replace("_", "")

        # Format descriptions: split on pipe and make content after pipe bold
        def format_description(text):
            text = str(text)
            if " | " in text:
                parts = text.split(" | ", 1)
                return f"{parts[0]}<br><strong>{parts[1]}</strong>"
            return text

        source_desc = format_description(row["source_full_sentence"])
        target_desc = format_description(row["target_full_sentence"])

        rows.append(f"""                <tr>
                    <td class="ref-id">{row["source_ref_id"]}</td>
                    <td class="description">{source_desc}</td>
                    <td><span class="relationship {relationship_class}">{row["relationship"]}</span></td>
                    <td class="ref-id">{row["target_ref_id"]}</td>
                    <td class="description">{target_desc}</td>
                    <td class="checkbox-cell"><input type="checkbox" id="review_{idx}"></td>
                </tr>""")

    html_content = html_template.format(
        total_mappings=len(df), table_rows="\n".join(rows)
    )

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"HTML review file created: {output_html}")


def main():
    parser = argparse.ArgumentParser(
        description="Prepare mapping review from CSV output"
    )
    parser.add_argument("input_csv", help="Input CSV file with mapping results")
    parser.add_argument(
        "--excel", help="Output Excel file (default: input_review.xlsx)", default=None
    )
    parser.add_argument(
        "--html", help="Output HTML file (default: input_review.html)", default=None
    )
    parser.add_argument(
        "--format",
        choices=["excel", "html", "both"],
        default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--favor-equals",
        action="store_true",
        help='For each source item, show only "equal" relationships if available, otherwise show all matches',
    )

    args = parser.parse_args()

    # Determine output file names
    input_path = Path(args.input_csv)
    base_name = input_path.stem

    excel_output = args.excel or f"{base_name}_review.xlsx"
    html_output = args.html or f"{base_name}_review.html"

    # Generate requested formats
    if args.format in ["excel", "both"]:
        create_excel_review(
            args.input_csv, excel_output, favor_equals=args.favor_equals
        )

    if args.format in ["html", "both"]:
        create_html_review(args.input_csv, html_output, favor_equals=args.favor_equals)


if __name__ == "__main__":
    main()
