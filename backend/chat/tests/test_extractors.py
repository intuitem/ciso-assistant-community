import io

import typst

from chat.extractors import extract_pdf


def test_extract_pdf_keeps_text_and_page_numbers():
    pdf = typst.compile(
        b"Offline backups are tested monthly.\n#pagebreak()\n"
        b"Multi-factor authentication for remote access."
    )

    chunks = extract_pdf(io.BytesIO(pdf))

    assert [c.metadata["page"] for c in chunks] == [1, 2]
    assert "Offline backups are tested monthly." in chunks[0].text
    assert "Multi-factor authentication" in chunks[1].text
