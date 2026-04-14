"""分解 API エンドポイント"""

import logging

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from app.schemas.split import SplitExecuteRequest, SplitExecuteResponse
from app.schemas.merge import UploadedFileInfo
from app.services.split_service import SplitService
from app.services.upload_service import UploadService
from app.storage import get_storage

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_upload_service() -> UploadService:
    return UploadService(get_storage())


def _get_split_service() -> SplitService:
    return SplitService(get_storage())


@router.post("/upload", response_model=UploadedFileInfo, summary="分解対象 PDF アップロード")
async def upload_pdf(
    file: UploadFile = File(...),
    upload_svc: UploadService = Depends(_get_upload_service),
) -> UploadedFileInfo:
    """PDF をアップロードし、file_id とページ数を返す"""
    data = await file.read()
    file_id, page_count = upload_svc.upload(
        filename=file.filename or "upload.pdf",
        content_type=file.content_type or "application/pdf",
        data=data,
    )
    return UploadedFileInfo(
        file_id=file_id,
        original_filename=file.filename or "upload.pdf",
        page_count=page_count,
    )


@router.post(
    "/execute",
    summary="PDF 分解実行",
    response_class=Response,
    responses={
        200: {
            "content": {"application/zip": {}},
            "description": "分解済み PDF をまとめた ZIP",
        }
    },
)
async def execute_split(
    request: SplitExecuteRequest,
    split_svc: SplitService = Depends(_get_split_service),
) -> Response:
    """
    PDF を指定ルールで分解し、ZIP ファイルを返す。
    split_rule_type に応じて fixed_pages_count または custom_ranges を指定する。
    """
    zip_key, file_count = split_svc.split(
        file_id=request.file_id,
        split_rule_type=request.split_rule_type,
        filename_template=request.filename_template,
        fixed_pages_count=request.fixed_pages_count,
        custom_ranges_str=request.custom_ranges,
        original_filename=request.original_filename,
    )
    zip_bytes = get_storage().load(zip_key)

    # 一時ファイル削除
    try:
        get_storage().delete(zip_key)
    except Exception:
        logger.warning("Failed to delete temp output: %s", zip_key)

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="split_result.zip"'},
    )
