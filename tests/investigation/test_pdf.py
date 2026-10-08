from io import BytesIO

import pytest
from product_core.investigation.acquisition import extract_document
from pypdf import PdfWriter


def pdf(pages):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=100, height=100)
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


def test_pdf_page_limit_reports_unexamined_and_scanned_pages():
    document = extract_document(pdf(105), "application/pdf")
    assert document.metadata["total_pages"] == 105
    assert document.metadata["extracted_pages"] == 100
    assert document.metadata["partial"] is True
    assert document.metadata["scanned"] is True


def test_pdf_selected_ranges_preserve_physical_page_numbers():
    document = extract_document(pdf(5), "application/pdf", [[3, 4]])
    assert [p["page"] for p in document.metadata["pages"]] == [3, 4]
    assert document.metadata["extracted_pages"] == 2


def test_pdf_cannot_extract_more_than_one_hundred_pages():
    with pytest.raises(ValueError):
        extract_document(pdf(110), "application/pdf", [[1, 110]])
