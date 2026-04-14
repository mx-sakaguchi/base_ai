"""
DB 接続設定。

SQLAlchemy の Session を使い、将来 Azure SQL / Cosmos DB に差し替えやすいよう
DATABASE_URL を環境変数で切替可能にしている。
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# 環境変数 DATABASE_URL が未設定の場合は SQLite をデフォルト使用
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./pdf_tools.db")

# SQLite の場合は check_same_thread=False が必要
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """全テーブルを作成する（べき等）"""
    # モデルを import して Base.metadata に登録
    from app.models import preset  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI の Depends で使う DB セッションジェネレータ"""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
