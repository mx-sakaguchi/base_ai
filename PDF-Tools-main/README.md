# PDF Tools

PDF の「結合」と「分解」を行う Web アプリ。

- **バックエンド**: Python 3.11+ / FastAPI
- **フロントエンド**: HTML/CSS/Vanilla JS（Jinja2 テンプレート）
- **PDF 操作**: pypdf
- **DB**: SQLite（将来 Azure SQL / Cosmos DB に切替可）
- **ストレージ**: ローカル一時保存 / Azure Blob Storage（環境変数で切替）

---

## ディレクトリ構成

```
.
├── app/
│   ├── main.py               # FastAPI エントリポイント
│   ├── database.py           # SQLAlchemy 設定
│   ├── api/                  # ルーター（merge / split / presets）
│   ├── services/             # ビジネスロジック
│   ├── repositories/         # DB アクセス
│   ├── models/               # SQLAlchemy ORM モデル
│   ├── schemas/              # Pydantic スキーマ
│   ├── storage/              # ストレージ抽象化（local / azure）
│   ├── utils/                # ユーティリティ・例外定義
│   ├── templates/            # Jinja2 テンプレート
│   └── static/               # CSS / JS
├── tests/                    # ユニットテスト
├── pyproject.toml            # uv によるパッケージ管理
├── uv.lock
├── .env.example
├── startup.sh                # Azure App Service 起動スクリプト
└── README.md
```

---

## ローカル起動手順

### 前提

- Python 3.11 以上
- [uv](https://docs.astral.sh/uv/)

### 手順

```bash
# 1. リポジトリをクローン
git clone <repo-url>
cd <repo-dir>

# 2. 依存パッケージをインストール
uv sync

# 3. 環境変数を設定（.env ファイルを作成）
cp .env.example .env
# .env を編集して STORAGE_BACKEND=local などを確認

# 4. 起動
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

ブラウザで http://localhost:8000 にアクセス。

OpenAPI ドキュメントは http://localhost:8000/docs で確認できます。

---

## テスト実行

```bash
uv run pytest tests/ -v
```

---

## 環境変数一覧

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `STORAGE_BACKEND` | `local` | `local` または `azure` |
| `LOCAL_STORAGE_ROOT` | `/tmp/pdf_tools` | ローカル保存先ディレクトリ |
| `DATABASE_URL` | `sqlite:///./pdf_tools.db` | SQLAlchemy 接続 URL |
| `AZURE_STORAGE_CONNECTION_STRING` | ー | Azure Blob 接続文字列（azure 時） |
| `AZURE_STORAGE_ACCOUNT_NAME` | ー | Azure ストレージアカウント名（Managed Identity 時） |
| `AZURE_BLOB_CONTAINER` | `pdf-tools` | Blob コンテナ名 |

---

## Azure App Service デプロイ手順

### 前提

- Azure CLI インストール済み
- Azure サブスクリプション・リソースグループ作成済み

### 手順

```bash
# 1. App Service プランを作成（Linux / Python 3.11）
az appservice plan create \
  --name pdf-tools-plan \
  --resource-group <rg-name> \
  --sku B1 \
  --is-linux

# 2. Web App を作成
az webapp create \
  --name pdf-tools-app \
  --resource-group <rg-name> \
  --plan pdf-tools-plan \
  --runtime "PYTHON:3.11"

# 3. アプリ設定（環境変数）を登録
az webapp config appsettings set \
  --name pdf-tools-app \
  --resource-group <rg-name> \
  --settings \
    STORAGE_BACKEND=local \
    DATABASE_URL="sqlite:////home/site/wwwroot/pdf_tools.db"

# 4. 起動コマンドを設定
az webapp config set \
  --name pdf-tools-app \
  --resource-group <rg-name> \
  --startup-file "bash startup.sh"

# 5. ソースコードをデプロイ（ZIP デプロイ）
zip -r deploy.zip . -x ".git/*" ".venv/*" "__pycache__/*" "*.pyc"
az webapp deployment source config-zip \
  --name pdf-tools-app \
  --resource-group <rg-name> \
  --src deploy.zip
```

デプロイ後、`https://pdf-tools-app.azurewebsites.net` でアクセス可能。

---

## Azure Blob Storage への切り替え方法

### 1. パッケージを有効化

```bash
uv sync --extra azure
```

### 2. 環境変数を設定

```bash
# 接続文字列方式（開発・CI）
az webapp config appsettings set \
  --name pdf-tools-app \
  --resource-group <rg-name> \
  --settings \
    STORAGE_BACKEND=azure \
    AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=..."

# Managed Identity 方式（本番推奨）
az webapp config appsettings set \
  --name pdf-tools-app \
  --resource-group <rg-name> \
  --settings \
    STORAGE_BACKEND=azure \
    AZURE_STORAGE_ACCOUNT_NAME=your-storage-account
```

### 3. Managed Identity を有効化（本番推奨）

```bash
# Web App に System-assigned Managed Identity を付与
az webapp identity assign \
  --name pdf-tools-app \
  --resource-group <rg-name>

# Storage Blob Data Contributor ロールを付与
az role assignment create \
  --assignee <principal-id> \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<account>
```

コード変更なし。環境変数の切替のみで動作します。

---

## 分解機能: ZIP 構成仕様

分解結果 ZIP のファイル構成は以下の通りです。

```
{元ファイル名}/
  {元ファイル名}_001.pdf
  {元ファイル名}_002.pdf
  ...
```

例: `sample.pdf` を分解した場合

```
sample/
  sample_001.pdf
  sample_002.pdf
  sample_003.pdf
```

- フォルダ名は元PDFのファイル名（拡張子除く）をサニタイズした値
- 元ファイル名が取得できない場合は `split_result/` フォルダを使用
- フォルダ名に使えない文字（`\ / : * ? " < > |`）は自動的に `_` に置換

---

## 分解機能: ファイル名テンプレート仕様

分解後のファイル名はテンプレートで指定します。

### デフォルト値

```
{original_name}_{index:03d}.pdf
```

例: 元ファイル `report.pdf` → `report_001.pdf`, `report_002.pdf`, ...

### 使用可能なプレースホルダ

| プレースホルダ | 説明 | 例 |
|---|---|---|
| `{original_name}` | 元ファイル名（拡張子なし） | `report` |
| `{index}` | 連番（1始まり） | `1`, `2`, `3` |
| `{index:03d}` | ゼロ埋め連番 | `001`, `002`, `003` |
| `{start}` | 分割範囲の開始ページ番号 | `1`, `4`, `8` |
| `{end}` | 分割範囲の終了ページ番号 | `3`, `7`, `10` |

### ファイル名のサニタイズ

- `.pdf` は省略可（末尾に自動補完）
- 使用不可文字（`\ / : * ? " < > |`）は自動的に `_` に置換
- `../` などの危険な相対パスは除去
- サニタイズ後に空文字になる場合は `output` を使用

---

## 結合機能: 複数ファイル対応

- ドラッグ＆ドロップエリアに複数 PDF を一度にドロップ可能
- ファイル選択ダイアログでも複数選択可能
- PDF 以外のファイルが含まれていた場合は除外してエラーメッセージを表示（他ファイルは処理継続）
- 同名ファイルは UUID ベースの `file_id` で内部的に区別

---

## 結合機能: ページサムネイル表示

アップロード後、各ページのサムネイルを表示して並べ替えを行います。

- **実装方式**: フロントエンドで PDF.js (pdfjs-dist) を使用してブラウザ側でレンダリング
- サーバーサイドへの追加リクエストなし（ローカルファイルから描画）
- サムネイルは幅 80px に縮小して表示
- ページ数が多い場合は進捗状況を表示

### 追加依存ライブラリ（フロントエンド）

| ライブラリ | バージョン | 用途 | 導入方式 |
|---|---|---|---|
| pdfjs-dist | 4.4.168 | PDF サムネイル描画 | CDN（サーバーサイド不要） |
| SortableJS | 1.15.2 | ページ並べ替え | CDN（既存） |

CDN 読み込みに失敗した場合は自動的にテキストのみのプレースホルダを表示します。

---

## 制約と今後の改善案

### 現在の制約

| 項目 | 現状 |
|------|------|
| アップロード上限 | 50 MB / ファイル（`MAX_UPLOAD_BYTES`） |
| ページ数上限 | 1,000 ページ / ファイル |
| 一時ファイル削除 | 結合・分解の出力後に削除。アップロードファイルは残る（手動クリーンアップ必要） |
| 認証 | なし（後付け可能な構造） |
| プリセット対応 | 分解のみ（結合ルールのプリセットは未実装） |
| 並行アップロード | 単一ユーザー想定（session 分離なし） |

### 今後の改善案

1. **認証追加**: `app/main.py` に `AuthMiddleware` を追加するだけで対応可。FastAPI の `Depends` を活用して各エンドポイントに `current_user` を注入する構造を推奨。

2. **一時ファイル自動クリーンアップ**: 定期実行（Azure Functions タイマートリガー等）で `uploads/` ディレクトリを TTL ベースで削除。

3. **結合プリセット**: `mode: "merge"` でページ順序をプリセット保存できるよう schema と DB を拡張。

4. **非同期処理**: 大容量 PDF の結合・分解を Azure Service Bus + Worker に切り出し、進捗をポーリング。

5. **Azure SQL 移行**: `DATABASE_URL` を MSSQL 接続文字列に変更するだけで SQLAlchemy ORM が動作する。マイグレーションには Alembic を導入推奨。

6. **CORS 設定**: SPA 分離構成にする場合は `fastapi.middleware.cors.CORSMiddleware` を追加。

7. **レート制限**: `slowapi` 等で IP ベースのレート制限を導入し DoS 対策を強化。
