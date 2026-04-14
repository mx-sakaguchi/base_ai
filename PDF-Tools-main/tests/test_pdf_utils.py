"""pdf_utils のユニットテスト"""

import io

import pytest
from pypdf import PdfWriter

from app.utils.exceptions import InvalidPDFError
from app.utils.pdf_utils import get_page_count, validate_pdf_bytes


def make_pdf(page_count: int) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class TestValidatePdfBytes:
    def test_valid_pdf_passes(self):
        validate_pdf_bytes(make_pdf(1))  # should not raise

    def test_invalid_magic_raises(self):
        with pytest.raises(InvalidPDFError, match="マジックバイト"):
            validate_pdf_bytes(b"not a pdf")

    def test_corrupted_pdf_raises(self):
        with pytest.raises(InvalidPDFError):
            # %PDF- から始まるが中身が壊れている
            validate_pdf_bytes(b"%PDF-1.4\ncorrupted content")


class TestGetPageCount:
    def test_correct_page_count(self):
        for n in [1, 5, 10]:
            assert get_page_count(make_pdf(n)) == n
