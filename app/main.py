from html import escape
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.extractor import ArticleExtractionError, extract_article
from app.llm import rewrite_article
from app.wordpress import markdown_to_html, save_draft


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

app = FastAPI(title="記事編集アプリ")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "default_template": (
                "見出しを整理し、要点が伝わる自然な日本語の記事にしてください。"
                "冒頭に短い導入を置き、H2・H3見出しを使って構成してください。"
            )
        },
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
        rewritten = rewrite_article(source, template)
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
            "markdown": rewritten,
            "preview_html": markdown_to_html(rewritten),
        },
    )


@app.post("/save", response_class=HTMLResponse)
def save(title: str = Form(""), markdown: str = Form("")):
    if not title.strip() or not markdown.strip():
        return HTMLResponse(
            '<p class="status status-error">タイトルと本文を入力してください。</p>'
        )

    try:
        saved = save_draft(title, markdown)
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
