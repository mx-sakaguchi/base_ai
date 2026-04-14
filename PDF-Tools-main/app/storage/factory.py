"""
ストレージバックエンドのファクトリ。

STORAGE_BACKEND 環境変数で切替:
  - "local"  → LocalStorage（デフォルト）
  - "azure"  → AzureBlobStorage
"""

import os
from functools import lru_cache

from app.storage.base import BaseStorage


@lru_cache(maxsize=1)
def get_storage() -> BaseStorage:
    backend = os.getenv("STORAGE_BACKEND", "local").lower()
    if backend == "azure":
        from app.storage.azure_storage import AzureBlobStorage

        return AzureBlobStorage()
    else:
        from app.storage.local_storage import LocalStorage

        return LocalStorage()
