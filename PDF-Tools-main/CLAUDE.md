# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Tyouseisan** is a Japanese PDF manipulation web application (merge/split) built with FastAPI + vanilla JavaScript, designed for Azure App Service deployment.

## Commands

**Setup:**
```bash
uv sync
```

**Run (development):**
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Run tests:**
```bash
uv run pytest tests/ -v
# Single test file:
uv run pytest tests/test_merge_service.py -v
# Single test:
uv run pytest tests/test_split_service.py::test_function_name -v
```

**API docs:** `http://localhost:8000/docs`

## Architecture

Layered architecture with clean separation:

1. **API layer** (`app/api/`): FastAPI routers — `merge.py`, `split.py`, `presets.py`
2. **Service layer** (`app/services/`): Business logic — `merge_service.py`, `split_service.py`, `upload_service.py`
3. **Repository layer** (`app/repositories/`): DB access — `preset_repository.py`
4. **Storage abstraction** (`app/storage/`): `BaseStorage` → `LocalStorage` or `AzureBlobStorage`, selected via `STORAGE_BACKEND` env var through `factory.py`
5. **Models/Schemas** (`app/models/`, `app/schemas/`): SQLAlchemy ORM and Pydantic models

**App entry point:** `app/main.py` — initializes DB on startup, mounts static files, registers routers, and serves `index.html` at `/`.

**Frontend:** Single-page app at `app/templates/index.html` with `app/static/js/app.js`. No build step — pure vanilla JS with SortableJS for drag-and-drop page reordering.

## Key Flows

**Merge:** Upload multiple PDFs → get `file_id`s → reorder pages via drag-and-drop → `POST /api/merge/execute` with `PageRef[]` (file_id + page_number) → download merged PDF.

**Split:** Upload single PDF → choose fixed-page or custom-range mode → `POST /api/split/execute` → download ZIP. Filename templates support `{index}`, `{start}`, `{end}`, `{original_name}`.

**Presets:** CRUD at `/api/presets/` for saving/reusing split configurations (merge presets not yet implemented).

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `STORAGE_BACKEND` | `local` | `local` or `azure` |
| `LOCAL_STORAGE_ROOT` | `/tmp/pdf_tools` | Local file storage path |
| `DATABASE_URL` | `sqlite:///./pdf_tools.db` | DB connection string |
| `AZURE_STORAGE_CONNECTION_STRING` | — | Azure Blob (alternative to Managed Identity) |
| `AZURE_STORAGE_ACCOUNT_NAME` | — | Azure Blob via Managed Identity |
| `AZURE_BLOB_CONTAINER` | `pdf-tools` | Azure Blob container name |

Copy `.env.example` to `.env` for local development.

## Constraints

- Max file size: 50 MB per PDF
- Max pages: 1,000 per PDF
- File type: `.pdf` only (validated by extension, Content-Type, and magic bytes)
- No authentication (single-user assumption; noted as easily retrofittable)
- Operations are synchronous — no background job processing
