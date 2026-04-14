"""ファイル名・拡張子のサニタイズ・バリデーション"""

import re
import unicodedata

# 許可する拡張子
ALLOWED_EXTENSIONS = {".pdf"}

# ファイル名に使えない文字（Windows / Linux 共通の危険文字）
_UNSAFE_CHARS = re.compile(r'[\\/:*?"<>|]')

# ファイル名の最大長
MAX_FILENAME_LENGTH = 255


def sanitize_filename(name: str) -> str:
    """
    ファイル名をサニタイズして安全な文字列を返す。
    - Unicode 正規化 (NFC)
    - パス区切り文字・危険文字を除去
    - 先頭・末尾のドット・スペースを除去
    - 空になった場合は "file" を返す
    """
    name = unicodedata.normalize("NFC", name)
    name = _UNSAFE_CHARS.sub("_", name)
    # ディレクトリトラバーサル防止
    name = name.replace("..", "_")
    name = name.strip(". _")
    name = name[:MAX_FILENAME_LENGTH]
    return name or "file"


def validate_extension(filename: str) -> None:
    """PDF 拡張子以外は ValueError を送出"""
    from pathlib import Path

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"拡張子 '{ext}' は許可されていません（許可: .pdf）")


def validate_content_type(content_type: str) -> None:
    """Content-Type が PDF でない場合は ValueError を送出"""
    allowed = {"application/pdf", "application/x-pdf"}
    # ブラウザによっては "application/pdf; charset=..." と来ることがある
    base_type = content_type.split(";")[0].strip().lower()
    if base_type not in allowed:
        raise ValueError(f"Content-Type '{content_type}' は許可されていません")
