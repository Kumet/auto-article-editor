from html import escape
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth import require_basic_auth
from app.extractor import ArticleExtractionError, extract_article
from app.llm import rewrite_article
from app.settings import load_settings, save_settings, settings_are_ephemeral
from app.wordpress import (
    WordPressConnectionError,
    sanitize_article_html,
    save_draft,
    test_wordpress_connection,
)


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

app = FastAPI(title="記事編集アプリ")
app.middleware("http")(require_basic_auth)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    settings = load_settings()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "active_tab": "editor",
            "default_template": settings["default_template"],
            "wp_configured": bool(settings["wp_url"]),
        },
    )


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "active_tab": "settings",
            "settings": load_settings(),
            "settings_ephemeral": settings_are_ephemeral(),
            "message": None,
            "error": None,
        },
    )


@app.post("/settings", response_class=HTMLResponse)
def update_settings(
    request: Request,
    default_template: str = Form(""),
    wp_url: str = Form(""),
):
    try:
        settings = save_settings(default_template, wp_url)
    except (OSError, ValueError) as exc:
        return templates.TemplateResponse(
            request=request,
            name="settings.html",
            context={
                "active_tab": "settings",
                "settings": {
                    "default_template": default_template,
                    "wp_url": wp_url,
                },
                "settings_ephemeral": settings_are_ephemeral(),
                "message": None,
                "error": str(exc),
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "active_tab": "settings",
            "settings": settings,
            "settings_ephemeral": settings_are_ephemeral(),
            "message": (
                "設定を一時保存しました。Render Freeでは再起動時に環境変数の値へ戻ります。"
                if settings_are_ephemeral()
                else "設定を保存しました。"
            ),
            "error": None,
        },
    )


@app.post("/settings/test-wordpress", response_class=HTMLResponse)
def check_wordpress_connection(request: Request, wp_url: str = Form("")):
    try:
        connection = test_wordpress_connection(wp_url)
    except WordPressConnectionError as exc:
        return templates.TemplateResponse(
            request=request,
            name="wordpress_connection_status.html",
            context={"error": str(exc), "connection": None},
        )

    return templates.TemplateResponse(
        request=request,
        name="wordpress_connection_status.html",
        context={"error": None, "connection": connection},
    )


@app.get("/guide", response_class=HTMLResponse)
def guide(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="guide.html",
        context={"active_tab": "guide"},
    )


@app.post("/generate", response_class=HTMLResponse)
def generate(request: Request, url: str = Form(""), template: str = Form("")):
    if not url.strip() or not template.strip():
        return templates.TemplateResponse(
            request=request,
            name="preview.html",
            context={"error": "URLと出力形式を入力してください。"},
        )

    try:
        article = extract_article(url)
        source = f"# {article['title']}\n\n{article['content']}"
        content = sanitize_article_html(rewrite_article(source, template))
        if not content:
            raise RuntimeError("AIから記事本文が返されませんでした。")
    except (ArticleExtractionError, RuntimeError) as exc:
        return templates.TemplateResponse(
            request=request,
            name="preview.html",
            context={"error": str(exc)},
        )
    except Exception:
        return templates.TemplateResponse(
            request=request,
            name="preview.html",
            context={"error": "記事の生成中に予期しないエラーが発生しました。"},
        )

    return templates.TemplateResponse(
        request=request,
        name="preview.html",
        context={
            "error": None,
            "title": article["title"],
            "content": content,
        },
    )


@app.post("/save", response_class=HTMLResponse)
def save(title: str = Form(""), content: str = Form("")):
    if not title.strip() or not content.strip():
        return HTMLResponse(
            '<p class="status status-error">タイトルと本文を入力してください。</p>'
        )

    try:
        settings = load_settings()
        saved = save_draft(title, content, settings["wp_url"])
    except requests.RequestException:
        return HTMLResponse(
            '<p class="status status-error">'
            "WordPressへの保存に失敗しました。接続情報とREST APIの状態を確認してください。"
            "</p>"
        )
    except RuntimeError as exc:
        return HTMLResponse(
            f'<p class="status status-error">{escape(str(exc))}</p>'
        )

    if not saved:
        return HTMLResponse(
            '<p class="status status-error">WordPressへの保存に失敗しました。</p>'
        )

    return HTMLResponse(
        '<p class="status status-success">WordPressへ下書き保存しました。</p>'
    )
