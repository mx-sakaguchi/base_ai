"""プリセット Repository — DB アクセスをここに集約する"""

from sqlalchemy.orm import Session

from app.models.preset import Preset
from app.schemas.preset import PresetCreate, PresetUpdate


class PresetRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[Preset]:
        return self._db.query(Preset).order_by(Preset.created_at.desc()).all()

    def get_by_id(self, preset_id: int) -> Preset | None:
        return self._db.query(Preset).filter(Preset.id == preset_id).first()

    def create(self, data: PresetCreate) -> Preset:
        preset = Preset(**data.model_dump())
        self._db.add(preset)
        self._db.commit()
        self._db.refresh(preset)
        return preset

    def update(self, preset_id: int, data: PresetUpdate) -> Preset | None:
        preset = self.get_by_id(preset_id)
        if preset is None:
            return None
        for key, value in data.model_dump().items():
            setattr(preset, key, value)
        self._db.commit()
        self._db.refresh(preset)
        return preset

    def delete(self, preset_id: int) -> bool:
        preset = self.get_by_id(preset_id)
        if preset is None:
            return False
        self._db.delete(preset)
        self._db.commit()
        return True
