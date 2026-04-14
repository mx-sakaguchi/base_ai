"""プリセット CRUD API エンドポイント"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.preset_repository import PresetRepository
from app.schemas.preset import PresetCreate, PresetResponse, PresetUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_repo(db: Session = Depends(get_db)) -> PresetRepository:
    return PresetRepository(db)


@router.get("/", response_model=list[PresetResponse], summary="プリセット一覧")
def list_presets(repo: PresetRepository = Depends(_get_repo)) -> list[PresetResponse]:
    return repo.list_all()  # type: ignore[return-value]


@router.post("/", response_model=PresetResponse, status_code=201, summary="プリセット作成")
def create_preset(
    data: PresetCreate,
    repo: PresetRepository = Depends(_get_repo),
) -> PresetResponse:
    return repo.create(data)  # type: ignore[return-value]


@router.put("/{preset_id}", response_model=PresetResponse, summary="プリセット更新")
def update_preset(
    preset_id: int,
    data: PresetUpdate,
    repo: PresetRepository = Depends(_get_repo),
) -> PresetResponse:
    updated = repo.update(preset_id, data)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Preset {preset_id} not found")
    return updated  # type: ignore[return-value]


@router.delete("/{preset_id}", status_code=204, summary="プリセット削除")
def delete_preset(
    preset_id: int,
    repo: PresetRepository = Depends(_get_repo),
) -> None:
    deleted = repo.delete(preset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Preset {preset_id} not found")
