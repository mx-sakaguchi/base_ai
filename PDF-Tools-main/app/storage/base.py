"""ストレージ抽象基底クラス"""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseStorage(ABC):
    """
    ローカルストレージと Azure Blob Storage の両方に対応できるよう
    インターフェースを統一している。
    """

    @abstractmethod
    def save(self, data: bytes, key: str) -> str:
        """
        バイナリデータを保存し、後から参照するためのキー（パスまたは Blob名）を返す。
        key にはサブディレクトリを含めてよい（例: "uploads/abc123/file.pdf"）
        """
        ...

    @abstractmethod
    def load(self, key: str) -> bytes:
        """キーに対応するデータを読み込む"""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """キーに対応するデータを削除する"""
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        """キーが存在するか確認する"""
        ...

    def build_download_path(self, key: str) -> str:
        """ダウンロード URL / パスを生成する（サブクラスでオーバーライド可）"""
        return f"/api/files/{key}"
