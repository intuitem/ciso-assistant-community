"""
WARNING: The exported text must be modified before it can be used with ccb-cff-2023-03-01_framework_NL.py
"""
import fitz  # pymupdf

def is_footer(text):
    return "Versie" in text and "©" in text and "Pagina" in text

def extract_text_pages(pdf_path, start_page, end_page, output_txt):
    doc = fitz.open(pdf_path)
    with open(output_txt, "w", encoding="utf-8") as f:
        for i in range(start_page - 1, end_page):
            page = doc[i]
            blocks = sorted(page.get_text("blocks"), key=lambda b: (b[1], b[0]))
            filtered = [b for b in blocks if b[6] == 0 and b[4].strip() and not is_footer(b[4])]
            
            f.write(f"--- Page {i+1} ---\n")
            for b in filtered:
                f.write(b[4].strip() + "\n")
            f.write("\n\n")
    doc.close()

# Exemple d’utilisation
extract_text_pages("./CyFUN_ESSENTIEEL_V2023-03-01_N_update 2024.pdf", 8, 76, "extract.txt")
