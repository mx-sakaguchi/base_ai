"""
PDF 分解サービス。

- fixed_pages: 固定ページ数ごとに分割
- custom_ranges: 任意範囲ごとに分割
分割結果を ZIP にまとめてストレージに保存する。

ZIP 内構成:
  {folder_name}/
    {output_001.pdf}
    {output_002.pdf}
    ...
folder_name は元ファイル名（拡張子なし）をサニタイズした値。
元ファイル名が取得できない場合は 'split_result' を使用する。
"""

import io
import logging
import re
import zipfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from app.services.upload_service import UploadService
from app.storage.base import BaseStorage
from app.utils.exceptions import ValidationError
from app.utils.file_utils import sanitize_filename
from app.utils.filename_utils import render_filename

logger = logging.getLogger(__name__)


def parse_custom_ranges(raw: str) -> list[tuple[int, int]]:
    """
    "1-3,4-7,8-10" 形式の文字列をパースして (start, end) のリストを返す。
    ページ番号は 1始まり。
    """
    raw = raw.strip()
    ranges: list[tuple[int, int]] = []

    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        match = re.fullmatch(r"(\d+)-(\d+)", part)
        if not match:
            raise ValidationError(
                f"範囲指定 '{part}' が不正です。'start-end' 形式で指定してください"
            )
        start, end = int(match.group(1)), int(match.group(2))
        if start < 1:
            raise ValidationError(f"ページ番号は 1 以上である必要があります（'{part}'）")
        if start > end:
            raise ValidationError(
                f"開始ページ {start} が終了ページ {end} より大きい（'{part}'）"
            )
        ranges.append((start, end))

    if not ranges:
        raise ValidationError("有効な範囲指定がありません")
    return ranges


def _make_zip_folder_name(original_filename: str) -> str:
    """
    元ファイル名（パス含む可能性あり）から ZIP 内フォルダ名を決定する。

    優先順位:
      1. 元ファイル名の stem（拡張子なし）をサニタイズした値
      2. stem が空・取得不可の場合は 'split_result'
    """
    if not original_filename:
        return "split_result"
    stem = Path(original_filename).stem.strip()
    if not stem:
        return "split_result"
    sanitized = sanitize_filename(stem)
    # sanitize_filename は内容がすべて不正文字の場合 "file" を返す。
    # その場合も元名由来として使用するが、真に空だった場合のみ split_result を使う。
    return sanitized


class SplitService:
    def __init__(self, storage: BaseStorage) -> None:
        self._storage = storage
        self._upload_svc = UploadService(storage)

    def split(
        self,
        file_id: str,
        split_rule_type: str,
        filename_template: str,
        fixed_pages_count: int | None = None,
        custom_ranges_str: str | None = None,
        original_filename: str = "",
    ) -> tuple[str, int]:
        """
        PDF を分割して ZIP を作成し、ストレージキーとファイル数を返す。

        Args:
            original_filename: 元ファイル名（ZIP フォルダ名・{original_name} に使用）

        Returns:
            (zip_key, file_count)
        """
        data = self._upload_svc.load(file_id)
        reader = PdfReader(io.BytesIO(data))
        total_pages = len(reader.pages)

        # {original_name} テンプレート変数: 元ファイル名の stem をサニタイズして使用
        stem = Path(original_filename).stem.strip() if original_filename else ""
        original_name = sanitize_filename(stem) if stem else f"file_{file_id[:8]}"

        # ZIP 内フォルダ名
        folder_name = _make_zip_folder_name(original_filename)

        # ページ範囲リストを生成
        if split_rule_type == "fixed_pages":
            if not fixed_pages_count:
                raise ValidationError("fixed_pages_count が指定されていません")
            ranges = self._build_fixed_ranges(total_pages, fixed_pages_count)
        elif split_rule_type == "custom_ranges":
            if not custom_ranges_str:
                raise ValidationError("custom_ranges が指定されていません")
            ranges = parse_custom_ranges(custom_ranges_str)
            # 範囲外チェック
            for start, end in ranges:
                if end > total_pages:
                    raise ValidationError(
                        f"ページ {end} は PDF の総ページ数 {total_pages} を超えています"
                    )
        else:
            raise ValidationError(f"不明な split_rule_type: {split_rule_type}")

        # 各範囲で PDF を生成して ZIP に格納
        # ZIP 構成: {folder_name}/{output_file.pdf}
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, (start, end) in enumerate(ranges, start=1):
                pdf_bytes = self._extract_pages(reader, start, end)
                fname = render_filename(
                    filename_template,
                    index=idx,
                    start=start,
                    end=end,
                    original_name=original_name,
                )
                # フォルダ内に格納することで解凍時に整理された構造になる
                zf.writestr(f"{folder_name}/{fname}", pdf_bytes)

        zip_bytes = zip_buf.getvalue()
        zip_key = f"outputs/split/{file_id}.zip"
        self._storage.save(zip_bytes, zip_key)

        file_count = len(ranges)
        logger.info(
            "Split file_id=%s into %d files → %s (%d bytes) [folder=%s]",
            file_id,
            file_count,
            zip_key,
            len(zip_bytes),
            folder_name,
        )
        return zip_key, file_count

    @staticmethod
    def _build_fixed_ranges(
        total_pages: int, page_size: int
    ) -> list[tuple[int, int]]:
        """総ページ数と固定サイズから範囲リストを生成する"""
        ranges = []
        start = 1
        while start <= total_pages:
            end = min(start + page_size - 1, total_pages)
            ranges.append((start, end))
            start = end + 1
        return ranges

    @staticmethod
    def _extract_pages(reader: PdfReader, start: int, end: int) -> bytes:
        """PDF の start〜end ページ（1始まり）を抽出してバイト列で返す"""
        writer = PdfWriter()
        for page_idx in range(start - 1, end):
            writer.add_page(reader.pages[page_idx])
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()
