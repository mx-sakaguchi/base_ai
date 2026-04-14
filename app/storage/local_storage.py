"""ローカルファイルシステムへの保存実装"""

import logging
import os
from pathlib import Path

from app.storage.base import BaseStorage

logger = logging.getLogger(__name__)

# ローカル保存先のルートディレクトリ（環境変数で変更可）
_DEFAULT_ROOT = Path(os.getenv("LOCAL_STORAGE_ROOT", "/tmp/pdf_tools"))


class LocalStorage(BaseStorage):
    def __init__(self, root: Path = _DEFAULT_ROOT) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        """
        パストラバーサル防止:
        key に ".." が含まれる場合は ValueError を送出する。
        """
        # key を正規化してルート外へのアクセスを防ぐ
        resolved = (self._root / key).resolve()
        if not str(resolved).startswith(str(self._root.resolve())):
            raise ValueError(f"Invalid storage key: {key}")
        return resolved

    def save(self, data: bytes, key: str) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        logger.debug("Saved %d bytes to %s", len(data), path)
        return key

    def load(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()
            logger.debug("Deleted %s", path)

    def exists(self, key: str) -> bool:
        try:
            return self._resolve(key).exists()
        except ValueError:
            return False
