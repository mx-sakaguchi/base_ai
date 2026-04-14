"""プリセット ORM モデル"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Preset(Base):
    __tablename__ = "presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    preset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False, default="split")

    # split_rule_type: "fixed_pages" | "custom_ranges"
    split_rule_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # fixed_pages_count: fixed_pages の場合に使用
    fixed_pages_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # custom_ranges: "1-3,4-7,8-10" 形式の文字列
    custom_ranges: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ファイル名テンプレート例: "invoice_{index:03d}.pdf"
    filename_template: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
