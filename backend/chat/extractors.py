"""
Document text extraction and chunking for RAG ingestion.
Each extractor handles a specific file type and produces semantically meaningful chunks.
"""

import csv
import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500  # Target tokens per chunk (approx 4 chars per token)
CHUNK_OVERLAP = 50  # Token overlap between chunks


@dataclass
class Chunk:
    """A chunk of text extracted from a document."""

    text: str
    index: int
    metadata: dict


def get_extractor(content_type: str):
    """Return the appropriate extractor for the given content type."""
    extractors = {
        "application/pdf": extract_pdf,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": extract_excel,
        "application/vnd.ms-excel": extract_excel,
        "text/csv": extract_csv,
        "text/plain": extract_text,
    }
    return extractors.get(content_type)


def extract_pdf(file) -> list[Chunk]:
    """Extract text from PDF, splitting by pages/paragraphs."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF not installed, cannot extract PDF")
        return []

    chunks = []
    file.seek(0)
    doc = fitz.open(stream=file.read(), filetype="pdf")

    for page_num, page in enumerate(doc):
        text = page.get_text().strip()
        if not text:
            continue

        # Split into paragraph-sized chunks
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) > CHUNK_SIZE * 4:
                if current_chunk:
                    chunks.append(
                        Chunk(
                            text=current_chunk.strip(),
                            index=len(chunks),
                            metadata={"page": page_num + 1},
                        )
                    )
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk:
            chunks.append(
                Chunk(
                    text=current_chunk.strip(),
                    index=len(chunks),
                    metadata={"page": page_num + 1},
                )
            )

    doc.close()
    return chunks


def extract_excel(file) -> list[Chunk]:
    """
    Extract from Excel preserving column semantics.
    Each row becomes a chunk with column headers as context.
    """
    try:
        import openpyxl
    except ImportError:
        logger.warning("openpyxl not installed, cannot extract Excel")
        return []

    chunks = []
    file.seek(0)
    wb = openpyxl.load_workbook(file, read_only=True, data_only=True)

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue

        # First row as headers
        headers = [str(h) if h else f"Column_{i}" for i, h in enumerate(rows[0])]

        # Each row becomes a chunk
        for row_idx, row in enumerate(rows[1:], start=2):
            parts = []
            for header, value in zip(headers, row):
                if value is not None and str(value).strip():
                    parts.append(f"{header}: {value}")

            if parts:
                text = f"Sheet: {sheet_name} | Row {row_idx}\n" + " | ".join(parts)
                chunks.append(
                    Chunk(
                        text=text,
                        index=len(chunks),
                        metadata={"sheet": sheet_name, "row": row_idx},
                    )
                )

    wb.close()
    return chunks


def extract_csv(file) -> list[Chunk]:
    """Extract from CSV with column headers as context."""
    chunks = []
    file.seek(0)

    content = file.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")

    reader = csv.reader(io.StringIO(content))
    headers = next(reader, None)
    if not headers:
        return []

    for row_idx, row in enumerate(reader, start=2):
        parts = []
        for header, value in zip(headers, row):
            if value and value.strip():
                parts.append(f"{header}: {value}")

        if parts:
            text = " | ".join(parts)
            chunks.append(
                Chunk(
                    text=text,
                    index=len(chunks),
                    metadata={"row": row_idx},
                )
            )

    return chunks


def extract_text(file) -> list[Chunk]:
    """Extract plain text, splitting into chunks by paragraph."""
    file.seek(0)
    content = file.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")

    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) > CHUNK_SIZE * 4:
            if current_chunk:
                chunks.append(
                    Chunk(text=current_chunk.strip(), index=len(chunks), metadata={})
                )
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk:
        chunks.append(Chunk(text=current_chunk.strip(), index=len(chunks), metadata={}))

    return chunks
