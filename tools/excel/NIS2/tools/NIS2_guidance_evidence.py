"""
Extract "GUIDANCE" (annotation) and "EXAMPLES OF EVIDENCE" (typical_evidence) from the NIS2 PDF file.
"""

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
    # Handle the specific case '; and  ' (Square Bullet)
    text = re.sub(r"; and\s+\s+", r"; and\n        * ", text)

    # Handle sub-bullets starting with '' (Square Bullet) after :, ; or .
    text = re.sub(r"(?<=[:;.\)])\s+\s+", r"\n        * ", text)
    
    # Handle the specific case '; and o '
    text = re.sub(r"; and o\s+", r"; and\n    o ", text, flags=re.IGNORECASE)
    
    # Handle sub-bullets starting with 'o' after :, ; or .
    text = re.sub(r"(?<=[:;.\)])\s+o\s+", r"\n    o ", text)
    
    # Add line break before each bullet point
    text = re.sub(r"•", r"\n•", text)
    
    return text

def append_footnotes_to_cell(text, footnotes_dict):
    if not text:
        return text
    matches = re.findall(r"\((\d+)\)", text)
    added_notes = set()
    first_add = True
    
    for num in matches:
        if num in footnotes_dict and num not in added_notes:
            if first_add:
                first_add = False
                text += "\n"
            text += f"\n({num}) {footnotes_dict[num]}"
            added_notes.add(num)
            del footnotes_dict[num]
    return text

def extract_records(lines):
    records = []
    current_ref = None
    current_annotation = ""
    current_evidence = ""
    mode = None  # None, "guidance", "evidence"
    in_tips = False
    footnotes = {}

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

            if ref_id.count('.') == 2:
                # case X.X.X (unchanged)
                in_tips = False
                i += 1
                while i < len(lines):
                    line = clean_line(lines[i])

                    if is_useless_line(line):
                        i += 1
                        continue

                    if re.match(r"^\(\d+\)", line):
                        # Begin collecting footnotes until next page marker
                        in_footnotes = True
                        current_number = None
                        
                        while i < len(lines):
                            line = clean_line(lines[i])
                            if is_page_marker(line):
                                if current_number:
                                    footnotes[current_number] = format_text(footnotes[current_number])
                                in_footnotes = False
                                current_number = None
                                break  # stop reading footnotes at page marker
                            
                            if re.match(r"^\d+$", line):
                                i += 1
                                continue  # IGNORE lines with only a number
                            
                            match = re.match(r"^\((\d+)\)\s*(.*)", line)
                            if match:
                                if current_number:
                                    footnotes[current_number] = format_text(footnotes[current_number])
                                current_number = match.group(1)
                                content = match.group(2)
                                footnotes[current_number] = content.strip()
                            elif current_number:
                                footnotes[current_number] += " " + line
                            i += 1
                        continue


                    if line.startswith("GUIDANCE"):
                        mode = "guidance"
                        i += 1
                        continue
                    elif line.startswith("EXAMPLES OF EVIDENCE"):
                        mode = "evidence"
                        i += 1
                        continue
                    elif line.startswith("TIPS") or line.startswith("TIP"):
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

            elif ref_id.count('.') == 1:
                # New case : ref_id = X.X and NOT followed by X.X.X.
                # Peek next non-useless line to check if starts with X.X.X.
                peek_i = i + 1
                while peek_i < len(lines) and is_useless_line(clean_line(lines[peek_i])):
                    peek_i += 1

                if peek_i < len(lines):
                    next_line = clean_line(lines[peek_i])
                    if not re.match(r"^\d+(\.\d+){2}(\.)?\s", next_line):
                        # It's the special case: X.X followed by guidance / evidence blocks without X.X.X
                        in_tips = False
                        i += 1
                        while i < len(lines):
                            line = clean_line(lines[i])

                            if is_useless_line(line):
                                i += 1
                                continue

                            if re.match(r"^\(\d+\)", line):
                                # Begin collecting footnotes until next page marker
                                in_footnotes = True
                                current_number = None
                                
                                while i < len(lines):
                                    line = clean_line(lines[i])
                                    if is_page_marker(line):
                                        if current_number:
                                            footnotes[current_number] = format_text(footnotes[current_number])
                                        in_footnotes = False
                                        current_number = None
                                        break  # stop reading footnotes at page marker
                                    
                                    if re.match(r"^\d+$", line):
                                        i += 1
                                        continue  # IGNORE lines with only a number
                                    
                                    match = re.match(r"^\((\d+)\)\s*(.*)", line)
                                    if match:
                                        if current_number:
                                            footnotes[current_number] = format_text(footnotes[current_number])
                                        current_number = match.group(1)
                                        content = match.group(2)
                                        footnotes[current_number] = content.strip()
                                    elif current_number:
                                        footnotes[current_number] += " " + line
                                    i += 1
                                    
                                continue

                            if line.startswith("GUIDANCE"):
                                mode = "guidance"
                                i += 1
                                continue
                            elif line.startswith("EXAMPLES OF EVIDENCE"):
                                mode = "evidence"
                                i += 1
                                continue
                            elif line.startswith("TIPS") or line.startswith("TIP"):
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

                        current_annotation = format_text(current_annotation)
                        current_evidence = format_text(current_evidence)

                        records.append({
                            "ref_id": current_ref,
                            "annotation": current_annotation.strip(),
                            "typical_evidence": current_evidence.strip()
                        })
                        continue  # don't increment i again
                    else:
                        # next line is X.X.X, treat as simple X.X ref (no inner blocks)
                        records.append({
                            "ref_id": current_ref,
                            "annotation": "",
                            "typical_evidence": ""
                        })
                else:
                    # no next line, treat as simple X.X ref
                    records.append({
                        "ref_id": current_ref,
                        "annotation": "",
                        "typical_evidence": ""
                    })
            else:
                # simple reference X. or others without inner blocks
                records.append({
                    "ref_id": current_ref,
                    "annotation": "",
                    "typical_evidence": ""
                })

        i += 1

    # Add footnotes
    for record in records:
        record["annotation"] = append_footnotes_to_cell(record["annotation"], footnotes)
        record["typical_evidence"] = append_footnotes_to_cell(record["typical_evidence"], footnotes)

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
    output_file = input_file.with_name("NIS2_guidance_evidence_output.xlsx")
    df.to_excel(output_file, index=False)
    print(f"✅ Excel file saved to: {output_file}")

if __name__ == "__main__":
    main()
