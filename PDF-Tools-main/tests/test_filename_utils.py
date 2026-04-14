"""filename_utils のユニットテスト"""

import pytest

from app.utils.filename_utils import render_filename
from app.utils.file_utils import sanitize_filename


class TestRenderFilename:
    def test_index_only(self):
        result = render_filename("invoice_{index}.pdf", index=1)
        assert result == "invoice_1.pdf"

    def test_zero_padded_index(self):
        result = render_filename("output_{index:03d}.pdf", index=5)
        assert result == "output_005.pdf"

    def test_start_end(self):
        result = render_filename("part_{start}-{end}.pdf", index=1, start=1, end=3)
        assert result == "part_1-3.pdf"

    def test_original_name(self):
        result = render_filename("{original_name}_{index}.pdf", index=2, original_name="report.pdf")
        assert result == "report_2.pdf"

    def test_auto_append_pdf_extension(self):
        result = render_filename("file_{index}", index=1)
        assert result.endswith(".pdf")

    def test_invalid_placeholder_raises(self):
        with pytest.raises(ValueError, match="不正なプレースホルダ"):
            render_filename("{__class__}.pdf", index=1)

    def test_sanitize_in_output(self):
        # テンプレートが展開されてもファイル名にスラッシュが含まれない
        result = render_filename("output_{index}.pdf", index=1, original_name="a/b/c.pdf")
        assert "/" not in result


class TestSanitizeFilename:
    def test_removes_path_separators(self):
        assert "/" not in sanitize_filename("a/b/c.pdf")
        assert "\\" not in sanitize_filename("a\\b.pdf")

    def test_removes_dotdot(self):
        assert ".." not in sanitize_filename("../../etc/passwd")

    def test_empty_becomes_file(self):
        assert sanitize_filename("") == "file"
        assert sanitize_filename("...") == "file"

    def test_normal_name_preserved(self):
        name = sanitize_filename("invoice_001.pdf")
        assert name == "invoice_001.pdf"

    def test_dangerous_chars_replaced(self):
        name = sanitize_filename('file<>:"/\\|?*name.pdf')
        assert "<" not in name
        assert ">" not in name
        assert ":" not in name
        assert '"' not in name
