"""
Simple PDF Text Extractor Script
-------------------------

This script extracts structured text from a PDF file using PyMuPDF (fitz),
preserving the relative layout of blocks as they appear on each page.

Features:
- Extracts text in reading order (top-to-bottom, left-to-right).
- Allows specifying a page range via --start and --end.
- Can optionally suppress page separators with --no-page-break.
- Outputs the result to a .txt file.

Usage (from command line):
    python simple_pdf_extractor.py input.pdf
    python simple_pdf_extractor.py input.pdf -o output.txt
    python simple_pdf_extractor.py input.pdf --start 3 --end 10 --no-page-break

Requirements:
    pip install PyMuPDF

WARNING:
    Text extraction from PDFs is inherently imperfect. The structure may not exactly
    match the visual layout, and line breaks or text order can be inconsistent,
    depending on how the PDF was generated. If you plan to apply post-processing scripts,
    you may need to manually adjust or clean some parts of the extracted text.
"""



import fitz  # PyMuPDF
import argparse
import os

def extract_structured_text(pdf_path, output_txt_path, start_page=None, end_page=None, show_page_break=True):
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF file: {e}")
        return

    total_pages = len(doc)
    start = max(0, (start_page - 1) if start_page else 0)
    end = min(total_pages, end_page if end_page else total_pages)

    if start >= end:
        print(f"Invalid page range: start={start + 1}, end={end}")
        return

    all_text = ""

    for page_num in range(start, end):
        page = doc[page_num]
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (round(b[1], 1), round(b[0], 1)))

        if show_page_break:
            all_text += f"\n--- PAGE {page_num + 1} ---\n\n"
        for block in blocks:
            text = block[4].strip()
            if text:
                all_text += text + "\n"

    try:
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(all_text)
        print(f"✅ Text successfully extracted to: {output_txt_path}")
    except Exception as e:
        print(f"Error writing output text file: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract structured text from a PDF.")
    parser.add_argument("pdf_path", help="Path to the input PDF file")
    parser.add_argument("-o", "--output", help="Path to output .txt file (default: same name as PDF)", default=None)
    parser.add_argument("--start", type=int, help="Start page number (1-based)", default=None)
    parser.add_argument("--end", type=int, help="End page number (1-based, inclusive)", default=None)
    parser.add_argument("--no-page-break", action="store_true", help="Do not include '--- PAGE X ---' separators")

    args = parser.parse_args()

    output_path = args.output or os.path.splitext(args.pdf_path)[0] + "_extracted.txt"
    extract_structured_text(
        args.pdf_path,
        output_path,
        args.start,
        args.end,
        show_page_break=not args.no_page_break
    )
