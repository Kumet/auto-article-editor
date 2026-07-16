import os
from urllib.parse import urlparse

import bleach
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError, Timeout


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


class WordPressConnectionError(RuntimeError):
    """Raised when WordPress credentials or draft permissions cannot be verified."""


def _connection_settings(wp_url: str) -> tuple[str, str, str]:
    normalized_wp_url = wp_url.strip().rstrip("/")
    parsed_wp_url = urlparse(normalized_wp_url)
    username = os.getenv("WP_USERNAME", "").strip()
    app_password = os.getenv("WP_APP_PASSWORD", "").strip()

    if not normalized_wp_url:
        raise WordPressConnectionError("WordPress URLを入力してください。")
    if parsed_wp_url.scheme not in {"http", "https"} or not parsed_wp_url.netloc:
        raise WordPressConnectionError(
            "WordPress URLはhttpまたはhttpsから入力してください。"
        )
    if not username or not app_password:
        raise WordPressConnectionError(
            "WP_USERNAMEまたはWP_APP_PASSWORDが設定されていません。"
        )

    return normalized_wp_url, username, app_password


def test_wordpress_connection(wp_url: str) -> dict[str, str]:
    """Verify WordPress authentication and permission to create draft posts."""
    normalized_wp_url, username, app_password = _connection_settings(wp_url)
    endpoint = f"{normalized_wp_url}/wp-json/wp/v2/users/me"

    try:
        response = requests.get(
            endpoint,
            auth=HTTPBasicAuth(username, app_password),
            params={"context": "edit"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except Timeout as exc:
        raise WordPressConnectionError(
            "WordPressへの接続がタイムアウトしました。URLとサーバーの状態を確認してください。"
        ) from exc
    except ConnectionError as exc:
        raise WordPressConnectionError(
            "WordPressへ接続できませんでした。URL、SSL、サーバーの状態を確認してください。"
        ) from exc
    except requests.RequestException as exc:
        raise WordPressConnectionError(
            "WordPressへの接続要求に失敗しました。URLを確認してください。"
        ) from exc

    if response.status_code in {401, 403}:
        raise WordPressConnectionError(
            "認証に失敗しました。WP_USERNAMEとWP_APP_PASSWORDを確認してください。"
        )
    if response.status_code == 404:
        raise WordPressConnectionError(
            "WordPress REST APIが見つかりません。サイトURLとREST APIの設定を確認してください。"
        )

    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WordPressConnectionError(
            f"WordPressがエラーを返しました（HTTP {response.status_code}）。"
        ) from exc

    try:
        user = response.json()
    except requests.JSONDecodeError as exc:
        raise WordPressConnectionError(
            "WordPressから正しいJSON応答を取得できませんでした。"
        ) from exc

    if not isinstance(user, dict):
        raise WordPressConnectionError(
            "WordPressからユーザー情報を取得できませんでした。"
        )

    capabilities = user.get("capabilities")
    if not isinstance(capabilities, dict) or not capabilities.get("edit_posts"):
        raise WordPressConnectionError(
            "認証には成功しましたが、このユーザーには記事の下書きを作成する権限がありません。"
        )

    return {
        "display_name": str(user.get("name") or username),
        "username": str(user.get("username") or username),
        "site_url": normalized_wp_url,
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
    try:
        normalized_wp_url, username, app_password = _connection_settings(wp_url)
    except WordPressConnectionError as exc:
        raise RuntimeError(str(exc)) from exc

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
