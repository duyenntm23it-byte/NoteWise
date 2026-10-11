from io import BytesIO

import pytest

from app.services.documents import extract_document


def _pdf_with_text() -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            b"<< /Length 58 >>\nstream\n"
            b"BT /F1 12 Tf 72 720 Td (Extracted PDF study notes) Tj ET\n"
            b"endstream"
        ),
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode())
        data.extend(body)
        data.extend(b"\nendobj\n")
    xref_offset = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010} 00000 n \n".encode())
    data.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(data)


def _docx_with_text() -> bytes:
    from docx import Document

    document = Document()
    document.add_paragraph("Extracted DOCX study notes")
    result = BytesIO()
    document.save(result)
    return result.getvalue()


def _pptx_with_text() -> bytes:
    from pptx import Presentation
    from pptx.util import Inches

    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    textbox = slide.shapes.add_textbox(
        Inches(1),
        Inches(1),
        Inches(5),
        Inches(1),
    )
    textbox.text = "Extracted PPTX study notes"
    result = BytesIO()
    presentation.save(result)
    return result.getvalue()


@pytest.mark.parametrize(
    (
        "filename",
        "media_type",
        "content",
        "expected_text",
        "expected_page_count",
        "expected_page_number",
    ),
    [
        (
            "notes.pdf",
            "application/pdf",
            _pdf_with_text,
            "Extracted PDF study notes",
            1,
            1,
        ),
        (
            "notes.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            _docx_with_text,
            "Extracted DOCX study notes",
            None,
            None,
        ),
        (
            "notes.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            _pptx_with_text,
            "Extracted PPTX study notes",
            1,
            1,
        ),
    ],
)
def test_extract_document_text_and_page_metadata(
    filename: str,
    media_type: str,
    content,
    expected_text: str,
    expected_page_count: int | None,
    expected_page_number: int | None,
) -> None:
    extracted = extract_document(content(), filename, media_type)

    assert extracted.page_count == expected_page_count
    assert len(extracted.chunks) == 1
    assert expected_text in extracted.chunks[0].content
    assert extracted.chunks[0].chunk_index == 0
    assert extracted.chunks[0].page_number == expected_page_number


def test_extract_document_rejects_corrupt_or_empty_content() -> None:
    with pytest.raises(ValueError):
        extract_document(b"%PDF-1.4\nbroken", "broken.pdf", "application/pdf")
