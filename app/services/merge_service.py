"""
PDF 結合サービス。

ページ単位で順序を指定し、指定順に新規 PDF を生成する。
"""

import io
import logging

from pypdf import PdfReader, PdfWriter

from app.schemas.merge import PageRef
from app.services.upload_service import UploadService
from app.storage.base import BaseStorage
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.file_utils import sanitize_filename

logger = logging.getLogger(__name__)


class MergeService:
    def __init__(self, storage: BaseStorage) -> None:
        self._storage = storage
        self._upload_svc = UploadService(storage)

    def merge(self, pages: list[PageRef], output_filename: str) -> str:
        """
        指定されたページ順序で PDF を結合し、ストレージに保存して key を返す。

        Args:
            pages: PageRef のリスト（file_id + 1始まりページ番号）
            output_filename: 出力ファイル名

        Returns:
            ストレージキー
        """
        if not pages:
            raise ValidationError("結合するページが指定されていません")

        # file_id をキーにして PdfReader をキャッシュ（同じファイルを複数回ロードしない）
        reader_cache: dict[str, PdfReader] = {}
        writer = PdfWriter()

        for ref in pages:
            if ref.file_id not in reader_cache:
                data = self._upload_svc.load(ref.file_id)
                reader_cache[ref.file_id] = PdfReader(io.BytesIO(data))

            reader = reader_cache[ref.file_id]
            total_pages = len(reader.pages)

            # ページ番号は 1始まり → 0始まりに変換
            page_idx = ref.page_number - 1
            if page_idx < 0 or page_idx >= total_pages:
                raise ValidationError(
                    f"file_id '{ref.file_id}' のページ番号 {ref.page_number} は "
                    f"範囲外です（1〜{total_pages}）"
                )

            writer.add_page(reader.pages[page_idx])

        # 出力
        buf = io.BytesIO()
        writer.write(buf)
        output_bytes = buf.getvalue()

        safe_name = sanitize_filename(output_filename)
        if not safe_name.endswith(".pdf"):
            safe_name += ".pdf"

        key = f"outputs/merge/{safe_name}"
        self._storage.save(output_bytes, key)

        logger.info(
            "Merged %d pages → %s (%d bytes)", len(pages), key, len(output_bytes)
        )
        return key
