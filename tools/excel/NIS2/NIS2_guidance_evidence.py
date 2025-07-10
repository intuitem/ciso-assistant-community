import re
import sys
import pandas as pd
from pathlib import Path

def clean_line(line):
    return line.strip()

def is_page_marker(line):
    return re.match(r"--- PAGE \d+ ---", line.strip())

def is_useless_line(line):
    stripped = line.strip()
    return (
        is_page_marker(stripped)
        or stripped in {"TECHNICAL IMPLEMENTATION GUIDANCE", "June 2025, version 1.0"}
        or re.match(r"^\d+$", stripped)
    )

def format_text(text):
    # Handle the specific case '; and o '
    text = re.sub(r"; and o\s+", r"; and\n    o ", text, flags=re.IGNORECASE)
    
    # Handle sub-bullets starting with 'o' after :, ; or .
    text = re.sub(r"(?<=[:;.\)])\s+o\s+", r"\n    o ", text)
    
    # Add line break before each bullet point
    text = re.sub(r"•", r"\n•", text)
    
    return text


def extract_records(lines):
    records = []
    current_ref = None
    current_annotation = ""
    current_evidence = ""
    mode = None  # None, "guidance", "evidence"
    in_tips = False

    i = 0
    while i < len(lines):
        line = clean_line(lines[i])

        if is_useless_line(line):
            i += 1
            continue

        # New reference X. / X.X / X.X.X.
        match_ref = re.match(r"^(\d+(\.\d+){0,2})(\.)?\s", line)
        if match_ref:
            ref_id = match_ref.group(1)
            current_ref = ref_id
            current_annotation = ""
            current_evidence = ""
            mode = None
            in_tips = False
            tips_wrote_for_guidance = False
            tips_wrote_for_evidence = False

            # If it's X.X.X → read inner blocks
            if ref_id.count('.') == 2:
                in_tips = False
                i += 1
                while i < len(lines):
                    line = clean_line(lines[i])

                    if is_useless_line(line):
                        i += 1
                        continue

                    # Switch section
                    if line.upper().startswith("GUIDANCE"):
                        mode = "guidance"
                        # in_tips = False
                        i += 1
                        continue
                    elif line.upper().startswith("EXAMPLES OF EVIDENCE"):
                        mode = "evidence"
                        # in_tips = False
                        i += 1
                        continue
                    elif line.upper().startswith("TIPS"):
                        in_tips = True
                        i += 1
                        continue
                    elif re.match(r"^(\d+(\.\d+){0,2})(\.)?\s", line):
                        break  # next reference

                    # Add content
                    if mode == "guidance":
                        if in_tips and not tips_wrote_for_guidance:
                            current_annotation += "\n\n[TIPS]\n" + line
                            tips_wrote_for_guidance = True
                        else:
                            current_annotation += " " + line
                    elif mode == "evidence":
                        if in_tips and not tips_wrote_for_evidence:
                            current_evidence += "\n\n[TIPS]\n" + line
                            tips_wrote_for_evidence = True
                        else:
                            current_evidence += " " + line
                    i += 1
                    
                # Apply formatting at the end, on the full accumulated text
                current_annotation = format_text(current_annotation)
                current_evidence = format_text(current_evidence)

                records.append({
                    "ref_id": current_ref,
                    "annotation": current_annotation.strip(),
                    "typical_evidence": current_evidence.strip()
                })
                continue  # don't increment i again
            else:
                # Simple reference X. or X.X
                records.append({
                    "ref_id": current_ref,
                    "annotation": "",
                    "typical_evidence": ""
                })

        i += 1

    return records

def main():
    if len(sys.argv) != 2:
        print("Usage: python convert_txt_to_excel.py <input_file.txt>")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    if not input_file.exists():
        print(f"❌ File not found: {input_file}")
        sys.exit(1)

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    records = extract_records(lines)

    df = pd.DataFrame(records)
    output_file = input_file.with_name(input_file.stem + "_output.xlsx")
    df.to_excel(output_file, index=False)
    print(f"✅ Excel file saved to: {output_file}")

if __name__ == "__main__":
    main()
