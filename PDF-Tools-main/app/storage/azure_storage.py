"""
Azure Blob Storage 実装。

STORAGE_BACKEND=azure に設定すると自動的にこのクラスが使われる。
azure-storage-blob パッケージが必要（requirements.txt に記載）。

接続方法:
  - AZURE_STORAGE_CONNECTION_STRING を設定する（開発・CI 向け）
  - または AZURE_STORAGE_ACCOUNT_NAME + Managed Identity（本番推奨）
"""

import logging
import os

from app.storage.base import BaseStorage

logger = logging.getLogger(__name__)

CONTAINER_NAME = os.getenv("AZURE_BLOB_CONTAINER", "pdf-tools")


class AzureBlobStorage(BaseStorage):
    def __init__(self) -> None:
        # インポートを遅延させ、azure SDK が入っていない環境でもクラス定義だけはできる
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError as e:
            raise ImportError(
                "azure-storage-blob が未インストールです。"
                "`pip install azure-storage-blob` を実行してください。"
            ) from e

        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")

        if conn_str:
            self._client = BlobServiceClient.from_connection_string(conn_str)
        elif account_name:
            # Managed Identity / DefaultAzureCredential を使用
            from azure.identity import DefaultAzureCredential

            credential = DefaultAzureCredential()
            self._client = BlobServiceClient(
                account_url=f"https://{account_name}.blob.core.windows.net",
                credential=credential,
            )
        else:
            raise EnvironmentError(
                "AZURE_STORAGE_CONNECTION_STRING または "
                "AZURE_STORAGE_ACCOUNT_NAME を設定してください"
            )

        # コンテナが存在しない場合は作成
        container_client = self._client.get_container_client(CONTAINER_NAME)
        if not container_client.exists():
            container_client.create_container()
            logger.info("Created Azure Blob container: %s", CONTAINER_NAME)

    def save(self, data: bytes, key: str) -> str:
        blob_client = self._client.get_blob_client(
            container=CONTAINER_NAME, blob=key
        )
        blob_client.upload_blob(data, overwrite=True)
        logger.debug("Uploaded %d bytes to blob: %s", len(data), key)
        return key

    def load(self, key: str) -> bytes:
        blob_client = self._client.get_blob_client(
            container=CONTAINER_NAME, blob=key
        )
        stream = blob_client.download_blob()
        return stream.readall()

    def delete(self, key: str) -> None:
        blob_client = self._client.get_blob_client(
            container=CONTAINER_NAME, blob=key
        )
        if blob_client.exists():
            blob_client.delete_blob()
            logger.debug("Deleted blob: %s", key)

    def exists(self, key: str) -> bool:
        blob_client = self._client.get_blob_client(
            container=CONTAINER_NAME, blob=key
        )
        return blob_client.exists()
