"""PDF バリデーション・情報取得ユーティリティ"""

import logging

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.utils.exceptions import InvalidPDFError

logger = logging.getLogger(__name__)

# PDF マジックバイト（%PDF-）
PDF_MAGIC = b"%PDF-"

# 最大ページ数（DoS 対策）
MAX_PAGES = int(1000)


def validate_pdf_bytes(data: bytes) -> None:
    """
    バイナリが有効な PDF か確認する。
    - マジックバイト確認
    - pypdf でのパース確認
    - ページ数上限チェック
    """
    if not data.startswith(PDF_MAGIC):
        raise InvalidPDFError("PDF のマジックバイトが不正です")
    try:
        import io

        reader = PdfReader(io.BytesIO(data))
        page_count = len(reader.pages)
    except PdfReadError as e:
        raise InvalidPDFError(f"PDF の読み込みに失敗しました: {e}") from e
    except Exception as e:
        raise InvalidPDFError(f"PDF の検証中にエラーが発生しました: {e}") from e

    if page_count == 0:
        raise InvalidPDFError("ページ数が 0 の PDF は受け付けられません")
    if page_count > MAX_PAGES:
        raise InvalidPDFError(
            f"ページ数 {page_count} は上限 {MAX_PAGES} を超えています"
        )


def get_page_count(data: bytes) -> int:
    """PDF のページ数を返す"""
    import io

    try:
        reader = PdfReader(io.BytesIO(data))
        return len(reader.pages)
    except PdfReadError as e:
        raise InvalidPDFError(f"PDF の読み込みに失敗しました: {e}") from e
