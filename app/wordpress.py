import html
import os

import markdown as markdown_lib
import requests
from requests.auth import HTTPBasicAuth


REQUEST_TIMEOUT_SECONDS = 30


def markdown_to_html(markdown_text: str) -> str:
    """Render Markdown while treating embedded HTML as plain text."""
    escaped_markdown = html.escape(markdown_text)
    return markdown_lib.markdown(
        escaped_markdown,
        extensions=["extra", "sane_lists"],
        output_format="html5",
    )


def save_draft(title: str, markdown: str) -> bool:
    """Save Markdown as a WordPress draft through the REST API."""
    wp_url = os.getenv("WP_URL", "").rstrip("/")
    username = os.getenv("WP_USERNAME")
    app_password = os.getenv("WP_APP_PASSWORD")

    if not wp_url or not username or not app_password:
        raise RuntimeError("WordPressの接続情報が設定されていません。")

    endpoint = f"{wp_url}/wp-json/wp/v2/posts"
    response = requests.post(
        endpoint,
        auth=HTTPBasicAuth(username, app_password),
        json={
            "title": title.strip(),
            "content": markdown_to_html(markdown),
            "status": "draft",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return True
