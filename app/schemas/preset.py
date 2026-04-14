"""プリセット Pydantic スキーマ"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PresetBase(BaseModel):
    preset_name: str = Field(..., min_length=1, max_length=255)
    mode: Literal["split"] = "split"
    split_rule_type: Literal["fixed_pages", "custom_ranges"]
    fixed_pages_count: int | None = Field(None, ge=1, le=1000)
    custom_ranges: str | None = Field(None, max_length=1000)
    filename_template: str = Field(..., min_length=1, max_length=255)

    @field_validator("fixed_pages_count")
    @classmethod
    def validate_fixed_pages(cls, v, info):
        rule_type = info.data.get("split_rule_type")
        if rule_type == "fixed_pages" and v is None:
            raise ValueError("fixed_pages_count は fixed_pages タイプの場合必須です")
        return v

    @field_validator("custom_ranges")
    @classmethod
    def validate_custom_ranges(cls, v, info):
        rule_type = info.data.get("split_rule_type")
        if rule_type == "custom_ranges" and not v:
            raise ValueError("custom_ranges は custom_ranges タイプの場合必須です")
        return v


class PresetCreate(PresetBase):
    pass


class PresetUpdate(PresetBase):
    pass


class PresetResponse(PresetBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
