"""結合 API スキーマ"""

from pydantic import BaseModel, Field


class PageRef(BaseModel):
    """結合時のページ参照（ファイルID + 1始まりページ番号）"""

    file_id: str = Field(..., description="アップロード時に払い出されたファイルID")
    page_number: int = Field(..., ge=1, description="1始まりのページ番号")


class MergeExecuteRequest(BaseModel):
    pages: list[PageRef] = Field(..., min_length=1, description="結合後のページ順序")
    output_filename: str = Field("merged.pdf", max_length=255)


class UploadedFileInfo(BaseModel):
    file_id: str
    original_filename: str
    page_count: int


class MergeExecuteResponse(BaseModel):
    download_url: str
