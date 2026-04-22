# CLAUDE.md

Claude Code がこのリポジトリで作業する際のガイドラインです。

## プロジェクト概要

**これは初心者向けのテンプレートリポジトリです。**

Python 3.14 + FastAPI + Azure App Service の最小構成テンプレートです。  
`app/main.py` を起点に機能を追加してください。

## コマンド

```bash
# セットアップ
uv sync

# 開発サーバー起動
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# テスト実行
uv run pytest tests/ -v

# パッケージ追加
uv add <package-name>
