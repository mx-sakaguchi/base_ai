#!/bin/bash
# Azure App Service の起動スクリプト
# App Service の "Startup Command" に: bash startup.sh

pip install uv
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
