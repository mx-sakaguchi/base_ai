"""
ファイル名テンプレートの評価・サニタイズ。

テンプレートは Python の str.format_map を使って展開するが、
任意コード実行を防ぐため許可されたプレースホルダのみを受け付ける。
"""

import re
import string
from pathlib import Path

from app.utils.file_utils import sanitize_filename

# 許可するプレースホルダ名
_ALLOWED_PLACEHOLDERS = {"index", "start", "end", "original_name"}

# フォーマット指定子付きプレースホルダを抽出する正規表現
# 例: {index:03d}, {start}, {original_name}
_PLACEHOLDER_RE = re.compile(r"\{(\w+)(?::[^}]*)?\}")


def _validate_template(template: str) -> None:
    """テンプレートに不正なプレースホルダが含まれないか検証する"""
    names = _PLACEHOLDER_RE.findall(template)
    for name in names:
        if name not in _ALLOWED_PLACEHOLDERS:
            raise ValueError(
                f"テンプレートに不正なプレースホルダ '{{{name}}}' が含まれています。"
                f"使用可能: {', '.join(sorted(_ALLOWED_PLACEHOLDERS))}"
            )


def render_filename(
    template: str,
    index: int,
    start: int | None = None,
    end: int | None = None,
    original_name: str = "file",
) -> str:
    """
    テンプレートを展開してサニタイズ済みファイル名を返す。

    使用可能なプレースホルダ:
      {index}         - 連番 (1始まり)
      {index:03d}     - ゼロ埋め連番
      {start}         - 開始ページ番号
      {end}           - 終了ページ番号
      {original_name} - 元ファイル名（拡張子なし）
    """
    _validate_template(template)

    original_stem = Path(original_name).stem

    # .pdf 拡張子がテンプレートに含まれていない場合は自動付与
    tpl = template if template.endswith(".pdf") else template + ".pdf"

    try:
        rendered = tpl.format(
            index=index,
            start=start if start is not None else index,
            end=end if end is not None else index,
            original_name=original_stem,
        )
    except (KeyError, ValueError) as e:
        raise ValueError(f"テンプレートの展開に失敗しました: {e}") from e

    # ファイル名部分だけサニタイズ（.pdf 拡張子は保持）
    stem = Path(rendered).stem
    sanitized = sanitize_filename(stem) + ".pdf"
    return sanitized
