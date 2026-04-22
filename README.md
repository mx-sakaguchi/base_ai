# AI Dev Template

**Claude Code + GitHub Codespaces + Azure App Service** で始める Python Web アプリ開発テンプレートです。

**fork → Codespaces 起動 → `claude` でログイン** だけで開発を開始できます。

---

## ディレクトリ構成

```
.
├── app/
│   └── main.py              # FastAPI アプリ本体（ここを編集して開発）
├── .claude/
│   └── settings.local.json  # Claude Code の安全設定
├── .devcontainer/
│   └── devcontainer.json    # Codespaces 環境定義
├── .github/
│   └── workflows/
│       └── deploy-aas-free.yml  # Azure 自動デプロイ
├── .env.example             # 環境変数のサンプル
├── .gitignore
├── pyproject.toml           # Python 依存パッケージ定義
└── README.md
```

---

## 1. Codespaces での開始手順

### Step 1: このリポジトリを fork する

GitHub 画面右上の **Fork** ボタンをクリック。

### Step 2: Codespaces を起動する

fork したリポジトリで **Code → Codespaces → Create codespace on main** をクリック。

> 初回は数分かかります。Python 3.14・uv・Claude Code が自動インストールされます。

### Step 3: Claude Code にログインする

Codespaces のターミナルで実行：

```bash
claude
```

ブラウザが開くので Anthropic アカウントでログインします。

> **注意**: APIキーはコードに書かないでください。`claude` コマンドのログインのみで使用できます。

### Step 4: 環境変数ファイルを作成する（必要な場合）

```bash
cp .env.example .env
# .env を編集して必要な値を設定する
```

---

## 2. ローカル実行

```bash
# 依存パッケージのインストール（初回のみ）
uv sync

# 開発サーバー起動
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

| URL | 内容 |
|-----|------|
| `http://localhost:8000` | トップページ |
| `http://localhost:8000/docs` | API ドキュメント (Swagger UI) |
| `http://localhost:8000/health` | ヘルスチェック |

---

## 3. 開発の進め方

Claude に話しかけながら開発できます：

```bash
claude
```

例：
```
POST /api/greet エンドポイントを app/main.py に追加してください。
name と age を受け取り、「Hello, {name}! あなたは{age}歳ですね。」を返します。
```

### テスト実行

```bash
uv run pytest tests/ -v
```

### パッケージ追加

```bash
uv add sqlalchemy
```

---

## 4. Azure App Service へのデプロイ

### Step 1: Azure App Service を作成する

```bash
az login
az group create --name my-app-rg --location japaneast
az appservice plan create --name my-app-plan --resource-group my-app-rg --sku F1 --is-linux
az webapp create --name my-app-xxxx --resource-group my-app-rg --plan my-app-plan --runtime "PYTHON|3.14"
```

> `my-app-xxxx` は世界で一意な名前にしてください。

### Step 2: GitHub Secrets に認証情報を登録する

```bash
az ad sp create-for-rbac \
  --name my-app-deploy \
  --role contributor \
  --scopes /subscriptions/<サブスクリプションID>/resourceGroups/my-app-rg \
  --sdk-auth
```

出力された JSON を、fork したリポジトリの **Settings → Secrets and variables → Actions** で `AZURE_CREDENTIALS` として登録。

### Step 3: ワークフローのアプリ名を変更する

`.github/workflows/deploy-aas-free.yml` の以下を編集：

```yaml
AZURE_WEBAPP_NAME: my-app-xxxx  # ← Step 1 で作成したアプリ名に変更
```

### Step 4: main ブランチに push する

GitHub Actions が自動でデプロイします（**Actions タブ**で確認）。

---

## 注意事項

- `.env` ファイルは **手動で作成**してください（`.env.example` を参考）
- `.env` は `.gitignore` 対象です。**絶対にコミットしないでください**
- APIキー・パスワードはすべて環境変数で管理してください
- このテンプレートは認証なしの構成です。本番運用時は認証を追加してください
- 機密情報（個人情報・医療情報など）の取り扱いには法令に従った追加対応が必要です

---