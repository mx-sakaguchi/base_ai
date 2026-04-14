"""結合 API エンドポイント"""

import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

from app.schemas.merge import MergeExecuteRequest, MergeExecuteResponse, UploadedFileInfo
from app.services.merge_service import MergeService
from app.services.upload_service import UploadService
from app.storage import get_storage
from app.utils.exceptions import AppError

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_upload_service() -> UploadService:
    return UploadService(get_storage())


def _get_merge_service() -> MergeService:
    return MergeService(get_storage())


@router.post("/upload", response_model=UploadedFileInfo, summary="PDF アップロード")
async def upload_pdf(
    file: UploadFile = File(...),
    upload_svc: UploadService = Depends(_get_upload_service),
) -> UploadedFileInfo:
    """
    PDF をアップロードし、file_id とページ数を返す。
    結合実行時は file_id を使ってページ参照する。
    """
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
    summary="PDF 結合実行",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "結合済み PDF",
        }
    },
)
async def execute_merge(
    request: MergeExecuteRequest,
    merge_svc: MergeService = Depends(_get_merge_service),
) -> Response:
    """
    指定されたページ順序で PDF を結合し、結合済み PDF を返す。
    pages リストにページ参照（file_id + page_number）を順番に指定する。
    """
    key = merge_svc.merge(request.pages, request.output_filename)
    pdf_bytes = get_storage().load(key)

    # 一時ファイル削除
    try:
        get_storage().delete(key)
    except Exception:
        logger.warning("Failed to delete temp output: %s", key)

    safe_name = request.output_filename
    if not safe_name.endswith(".pdf"):
        safe_name += ".pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )
