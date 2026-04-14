"""split_service / SplitService のユニットテスト（実 PDF を使用）"""

import io
import zipfile

import pytest
from pypdf import PdfReader, PdfWriter

from app.services.split_service import SplitService, _make_zip_folder_name, parse_custom_ranges
from app.storage.local_storage import LocalStorage
from app.utils.exceptions import ValidationError


# ---------- ヘルパー: テスト用 PDF 生成 ----------

def make_pdf(page_count: int) -> bytes:
    """指定ページ数の PDF バイト列を生成する"""
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ---------- parse_custom_ranges ----------

class TestParseCustomRanges:
    def test_single_range(self):
        ranges = parse_custom_ranges("1-3")
        assert ranges == [(1, 3)]

    def test_multiple_ranges(self):
        ranges = parse_custom_ranges("1-3,4-7,8-10")
        assert ranges == [(1, 3), (4, 7), (8, 10)]

    def test_single_page_range(self):
        ranges = parse_custom_ranges("2-2")
        assert ranges == [(2, 2)]

    def test_invalid_format_raises(self):
        with pytest.raises(ValidationError):
            parse_custom_ranges("abc")

    def test_start_greater_than_end_raises(self):
        with pytest.raises(ValidationError):
            parse_custom_ranges("5-3")

    def test_zero_start_raises(self):
        with pytest.raises(ValidationError):
            parse_custom_ranges("0-3")

    def test_empty_string_raises(self):
        with pytest.raises(ValidationError):
            parse_custom_ranges("")


# ---------- _make_zip_folder_name ----------

class TestMakeZipFolderName:
    def test_normal_filename(self):
        assert _make_zip_folder_name("sample.pdf") == "sample"

    def test_filename_with_spaces(self):
        # スペースはサニタイズ後も保持される
        result = _make_zip_folder_name("my report.pdf")
        assert result == "my report"

    def test_filename_with_unsafe_chars(self):
        # 使用不可文字は _ に置換される
        result = _make_zip_folder_name('file:name?.pdf')
        assert ":" not in result
        assert "?" not in result

    def test_empty_string_returns_split_result(self):
        assert _make_zip_folder_name("") == "split_result"

    def test_no_extension(self):
        # 拡張子なしでも stem として処理される
        assert _make_zip_folder_name("report") == "report"

    def test_only_unsafe_chars_returns_sanitized_or_split_result(self):
        # 結果が何らかの文字になることを確認
        result = _make_zip_folder_name("???.pdf")
        assert result  # 空でないことを確認


# ---------- SplitService ----------

@pytest.fixture
def tmp_storage(tmp_path):
    return LocalStorage(root=tmp_path)


@pytest.fixture
def split_svc(tmp_storage):
    return SplitService(tmp_storage)


@pytest.fixture
def uploaded_file_id(tmp_storage):
    """テスト用 PDF をストレージに直接保存して file_id を返す"""
    import uuid

    pdf_data = make_pdf(6)
    file_id = str(uuid.uuid4())
    tmp_storage.save(pdf_data, f"uploads/{file_id}/test.pdf")
    return file_id


class TestSplitService:
    def test_fixed_pages_split(self, split_svc, uploaded_file_id):
        key, count = split_svc.split(
            file_id=uploaded_file_id,
            split_rule_type="fixed_pages",
            filename_template="part_{index:02d}.pdf",
            fixed_pages_count=2,
        )
        assert count == 3  # 6ページ ÷ 2 = 3ファイル
        assert key.endswith(".zip")

    def test_fixed_pages_last_chunk(self, split_svc, uploaded_file_id):
        """7ページを3ページごとに割ると最後は1ページになる"""
        import uuid

        storage = split_svc._storage
        pdf_data = make_pdf(7)
        file_id = str(uuid.uuid4())
        storage.save(pdf_data, f"uploads/{file_id}/test.pdf")

        _, count = split_svc.split(
            file_id=file_id,
            split_rule_type="fixed_pages",
            filename_template="out_{index}.pdf",
            fixed_pages_count=3,
        )
        assert count == 3  # ceil(7/3) = 3

    def test_custom_ranges_split(self, split_svc, uploaded_file_id):
        key, count = split_svc.split(
            file_id=uploaded_file_id,
            split_rule_type="custom_ranges",
            filename_template="chapter_{index}.pdf",
            custom_ranges_str="1-2,3-4,5-6",
        )
        assert count == 3

    def test_out_of_range_page_raises(self, split_svc, uploaded_file_id):
        with pytest.raises(ValidationError):
            split_svc.split(
                file_id=uploaded_file_id,
                split_rule_type="custom_ranges",
                filename_template="out_{index}.pdf",
                custom_ranges_str="1-100",  # 6ページしかない
            )

    def test_missing_fixed_count_raises(self, split_svc, uploaded_file_id):
        with pytest.raises(ValidationError):
            split_svc.split(
                file_id=uploaded_file_id,
                split_rule_type="fixed_pages",
                filename_template="out_{index}.pdf",
                fixed_pages_count=None,
            )

    def test_zip_contains_correct_files_with_folder(self, split_svc, uploaded_file_id, tmp_storage):
        """ZIP 内ファイルは {folder_name}/{filename} の形式になること"""
        key, count = split_svc.split(
            file_id=uploaded_file_id,
            split_rule_type="fixed_pages",
            filename_template="p_{index:03d}.pdf",
            fixed_pages_count=2,
        )
        zip_bytes = tmp_storage.load(key)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
        assert len(names) == 3
        # original_filename 未指定 → フォルダ名は "split_result"
        assert "split_result/p_001.pdf" in names
        assert "split_result/p_002.pdf" in names
        assert "split_result/p_003.pdf" in names

    def test_zip_folder_uses_original_filename(self, split_svc, uploaded_file_id, tmp_storage):
        """original_filename が指定された場合、フォルダ名にその stem が使われる"""
        key, _ = split_svc.split(
            file_id=uploaded_file_id,
            split_rule_type="fixed_pages",
            filename_template="{original_name}_{index:03d}.pdf",
            fixed_pages_count=2,
            original_filename="sample_report.pdf",
        )
        zip_bytes = tmp_storage.load(key)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
        # フォルダ名は "sample_report"
        assert all(n.startswith("sample_report/") for n in names)
        assert "sample_report/sample_report_001.pdf" in names
        assert "sample_report/sample_report_002.pdf" in names
        assert "sample_report/sample_report_003.pdf" in names

    def test_zip_folder_defaults_when_no_original_filename(self, split_svc, uploaded_file_id, tmp_storage):
        """original_filename が空の場合、フォルダ名は 'split_result' になる"""
        key, _ = split_svc.split(
            file_id=uploaded_file_id,
            split_rule_type="fixed_pages",
            filename_template="part_{index}.pdf",
            fixed_pages_count=6,
            original_filename="",
        )
        zip_bytes = tmp_storage.load(key)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
        assert all(n.startswith("split_result/") for n in names)

    def test_original_name_template_uses_filename_stem(self, split_svc, uploaded_file_id, tmp_storage):
        """{original_name} テンプレートが元ファイル名の stem に展開されること"""
        key, _ = split_svc.split(
            file_id=uploaded_file_id,
            split_rule_type="fixed_pages",
            filename_template="{original_name}_{index:03d}.pdf",
            fixed_pages_count=6,
            original_filename="invoice.pdf",
        )
        zip_bytes = tmp_storage.load(key)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
        assert "invoice/invoice_001.pdf" in names
