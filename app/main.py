"""
FastAPI application entry point.

認証を後付けしやすいよう、ミドルウェア追加の余地を明示的に残している。
将来は app.add_middleware(AuthMiddleware, ...) をここに追加するだけでよい。
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import merge, presets, split
from app.database import init_db
from app.utils.exceptions import AppError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリ起動時に DB 初期化を行う"""
    logger.info("Starting up: initializing database")
    init_db()
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="PDF Tools",
    description="PDF 結合・分解 Web アプリ",
    version="1.0.0",
    lifespan=lifespan,
)

# --- 静的ファイル・テンプレート ---
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# --- API ルーター ---
app.include_router(merge.router, prefix="/api/merge", tags=["merge"])
app.include_router(split.router, prefix="/api/split", tags=["split"])
app.include_router(presets.router, prefix="/api/presets", tags=["presets"])


# --- グローバル例外ハンドラ ---
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning("AppError: %s", exc.message)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# --- フロントエンド ---
@app.get("/", include_in_schema=False)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")
