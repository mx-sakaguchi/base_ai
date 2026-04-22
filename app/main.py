"""
最小構成の FastAPI アプリケーション。
ここを起点に機能を追加してください。

セキュリティ方針:
- 環境変数で設定を外部化（secrets をコードに直書きしない）
- HTTPS のみを前提とした設計（Azure App Service は HTTPS を強制可能）
- 不要なポートは開放しない（80/443 のみ前提）
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="My App",
    description="Claude Code + Azure で作る Web アプリのテンプレートです",
    version="0.1.0",
)


@app.get("/", response_class=HTMLResponse)
def read_root() -> HTMLResponse:
    """トップページ"""
    html = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>My App</title>
        <style>
            body { font-family: sans-serif; max-width: 600px; margin: 80px auto; padding: 0 20px; }
            h1 { color: #333; }
            a { color: #0070f3; }
        </style>
    </head>
    <body>
        <h1>Hello, World!</h1>
        <p>FastAPI テンプレートが正常に動いています。</p>
        <ul>
            <li><a href="/docs">API ドキュメント (Swagger UI)</a></li>
            <li><a href="/health">ヘルスチェック</a></li>
            <li><a href="/api/hello?name=Claude">サンプル API</a></li>
        </ul>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/health")
def health_check() -> dict[str, str]:
    """ヘルスチェックエンドポイント（Azure App Service の監視用）"""
    return {"status": "ok"}


@app.get("/api/hello")
def hello(name: str = "World") -> dict[str, str]:
    """サンプル API エンドポイント。?name= で名前を渡せます"""
    return {"message": f"Hello, {name}!"}
