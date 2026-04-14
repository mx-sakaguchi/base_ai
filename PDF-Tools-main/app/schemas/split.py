"""分解 API スキーマ"""

from typing import Literal

from pydantic import BaseModel, Field


class SplitExecuteRequest(BaseModel):
    file_id: str = Field(..., description="アップロード時に払い出されたファイルID")
    split_rule_type: Literal["fixed_pages", "custom_ranges"]
    fixed_pages_count: int | None = Field(None, ge=1, le=1000)
    custom_ranges: str | None = Field(None, max_length=1000)
    filename_template: str = Field("{original_name}_{index:03d}.pdf", max_length=255)
    # ZIP 内フォルダ名・テンプレート {original_name} の展開に使用する元ファイル名
    original_filename: str = Field("", max_length=255, description="元ファイル名（ZIP フォルダ名・テンプレート展開に使用）")


class SplitExecuteResponse(BaseModel):
    download_url: str
    file_count: int
