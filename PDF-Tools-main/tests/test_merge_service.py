"""merge_service / MergeService のユニットテスト"""

import io
import uuid

import pytest
from pypdf import PdfReader, PdfWriter

from app.schemas.merge import PageRef
from app.services.merge_service import MergeService
from app.storage.local_storage import LocalStorage
from app.utils.exceptions import ValidationError


def make_pdf(page_count: int) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture
def tmp_storage(tmp_path):
    return LocalStorage(root=tmp_path)


@pytest.fixture
def merge_svc(tmp_storage):
    return MergeService(tmp_storage)


def upload_file(storage: LocalStorage, page_count: int) -> str:
    """テスト用 PDF をストレージに保存して file_id を返す"""
    pdf_data = make_pdf(page_count)
    file_id = str(uuid.uuid4())
    storage.save(pdf_data, f"uploads/{file_id}/test.pdf")
    return file_id


class TestMergeService:
    def test_merge_single_file_all_pages(self, merge_svc, tmp_storage):
        fid = upload_file(tmp_storage, 3)
        pages = [PageRef(file_id=fid, page_number=i) for i in range(1, 4)]
        key = merge_svc.merge(pages, "out.pdf")
        data = tmp_storage.load(key)
        reader = PdfReader(io.BytesIO(data))
        assert len(reader.pages) == 3

    def test_merge_reorder_pages(self, merge_svc, tmp_storage):
        fid = upload_file(tmp_storage, 3)
        # ページを逆順に結合
        pages = [PageRef(file_id=fid, page_number=3),
                 PageRef(file_id=fid, page_number=2),
                 PageRef(file_id=fid, page_number=1)]
        key = merge_svc.merge(pages, "reversed.pdf")
        data = tmp_storage.load(key)
        reader = PdfReader(io.BytesIO(data))
        assert len(reader.pages) == 3

    def test_merge_multiple_files(self, merge_svc, tmp_storage):
        fid_a = upload_file(tmp_storage, 2)
        fid_b = upload_file(tmp_storage, 2)
        pages = [
            PageRef(file_id=fid_a, page_number=1),
            PageRef(file_id=fid_b, page_number=2),
            PageRef(file_id=fid_a, page_number=2),
        ]
        key = merge_svc.merge(pages, "combo.pdf")
        data = tmp_storage.load(key)
        reader = PdfReader(io.BytesIO(data))
        assert len(reader.pages) == 3

    def test_invalid_page_number_raises(self, merge_svc, tmp_storage):
        fid = upload_file(tmp_storage, 2)
        pages = [PageRef(file_id=fid, page_number=99)]  # 存在しないページ
        with pytest.raises(ValidationError):
            merge_svc.merge(pages, "out.pdf")

    def test_empty_pages_raises(self, merge_svc):
        with pytest.raises(ValidationError):
            merge_svc.merge([], "out.pdf")

    def test_output_filename_sanitized(self, merge_svc, tmp_storage):
        fid = upload_file(tmp_storage, 1)
        pages = [PageRef(file_id=fid, page_number=1)]
        # スラッシュ入りファイル名でもパストラバーサルが起きないこと
        key = merge_svc.merge(pages, "../../etc/passwd")
        assert ".." not in key
