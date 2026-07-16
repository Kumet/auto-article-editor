import os

import bleach
import requests
from requests.auth import HTTPBasicAuth


REQUEST_TIMEOUT_SECONDS = 30
ALLOWED_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "em",
    "figcaption",
    "figure",
    "h2",
    "h3",
    "h4",
    "hr",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
}


def sanitize_article_html(content: str) -> str:
    """Remove unsafe markup before previewing or saving generated HTML."""
    return bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols={"http", "https", "mailto"},
        strip=True,
        strip_comments=True,
    )


def save_draft(title: str, content: str, wp_url: str) -> bool:
    """Save an HTML article as a WordPress draft through the REST API."""
    normalized_wp_url = wp_url.strip().rstrip("/")
    username = os.getenv("WP_USERNAME")
    app_password = os.getenv("WP_APP_PASSWORD")

    if not normalized_wp_url:
        raise RuntimeError("設定画面でWordPress URLを設定してください。")
    if not username or not app_password:
        raise RuntimeError("WordPressの接続情報が設定されていません。")

    endpoint = f"{normalized_wp_url}/wp-json/wp/v2/posts"
    response = requests.post(
        endpoint,
        auth=HTTPBasicAuth(username, app_password),
        json={
            "title": title.strip(),
            "content": sanitize_article_html(content),
            "status": "draft",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return True
