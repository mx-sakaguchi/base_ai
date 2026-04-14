"""
アップロードファイル管理サービス。

- ファイルを一時保存し UUID ベースの file_id を払い出す
- ストレージバックエンドに依存（LocalStorage / AzureBlobStorage）
"""

import logging
import uuid

from app.storage.base import BaseStorage
from app.utils.exceptions import FileTooLargeError, NotFoundError
from app.utils.file_utils import sanitize_filename, validate_content_type, validate_extension
from app.utils.pdf_utils import get_page_count, validate_pdf_bytes

logger = logging.getLogger(__name__)

# アップロード上限: 50 MB
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class UploadService:
    def __init__(self, storage: BaseStorage) -> None:
        self._storage = storage

    def upload(
        self, filename: str, content_type: str, data: bytes
    ) -> tuple[str, int]:
        """
        PDF をバリデートして保存する。
        Returns (file_id, page_count)
        """
        # サイズ制限
        if len(data) > MAX_UPLOAD_BYTES:
            raise FileTooLargeError(
                f"ファイルサイズ {len(data) // 1024 // 1024} MB は上限 "
                f"{MAX_UPLOAD_BYTES // 1024 // 1024} MB を超えています"
            )

        # 拡張子・Content-Type 検証
        validate_extension(filename)
        validate_content_type(content_type)

        # PDF バリデーション
        validate_pdf_bytes(data)

        # ページ数取得
        page_count = get_page_count(data)

        # ファイル名サニタイズ
        safe_name = sanitize_filename(filename)

        # file_id を採番して保存
        file_id = str(uuid.uuid4())
        key = f"uploads/{file_id}/{safe_name}"
        self._storage.save(data, key)

        logger.info("Uploaded file_id=%s pages=%d name=%s", file_id, page_count, safe_name)
        return file_id, page_count

    def load(self, file_id: str) -> bytes:
        """file_id に対応する PDF バイトを返す"""
        key = self._find_key(file_id)
        return self._storage.load(key)

    def delete(self, file_id: str) -> None:
        """一時ファイルを削除する"""
        key = self._find_key(file_id)
        self._storage.delete(key)
        logger.info("Deleted file_id=%s", file_id)

    def _find_key(self, file_id: str) -> str:
        """
        ローカルストレージの場合は uploads/<file_id>/ 配下を探す。
        Azure の場合はプレフィックスで検索が必要だが、
        ここでは file_id ディレクトリをスキャンする簡易実装。
        """
        # UUID 形式チェック（セキュリティ: path traversal 防止）
        try:
            uuid.UUID(file_id)
        except ValueError as e:
            raise NotFoundError(f"Invalid file_id: {file_id}") from e

        from app.storage.local_storage import LocalStorage
        import os

        if isinstance(self._storage, LocalStorage):
            upload_dir = self._storage._root / "uploads" / file_id
            if upload_dir.exists():
                files = list(upload_dir.iterdir())
                if files:
                    rel = files[0].relative_to(self._storage._root)
                    return str(rel)

        raise NotFoundError(f"file_id '{file_id}' が見つかりません")
