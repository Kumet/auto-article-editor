import os
from urllib.parse import urlparse

import bleach
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import (
    ConnectionError,
    ProxyError,
    SSLError,
    Timeout,
    TooManyRedirects,
)


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

    def __init__(
        self,
        message: str,
        *,
        cause: str,
        evidence: list[str] | None = None,
        suggestions: list[str] | None = None,
        details: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.cause = cause
        self.evidence = evidence or []
        self.suggestions = suggestions or []
        self.details = details or {}


def _connection_error(
    message: str,
    cause: str,
    *,
    evidence: list[str] | None = None,
    suggestions: list[str] | None = None,
    details: dict[str, str] | None = None,
) -> WordPressConnectionError:
    return WordPressConnectionError(
        message,
        cause=cause,
        evidence=evidence,
        suggestions=suggestions,
        details=details,
    )


def _connection_settings(wp_url: str) -> tuple[str, str, str]:
    normalized_wp_url = wp_url.strip().rstrip("/")
    parsed_wp_url = urlparse(normalized_wp_url)
    username = os.getenv("WP_USERNAME", "").strip()
    app_password = os.getenv("WP_APP_PASSWORD", "").strip()

    if not normalized_wp_url:
        raise _connection_error(
            "WordPress URLを入力してください。",
            "接続先URLが未入力です。",
            suggestions=["設定画面へWordPressサイトのトップURLを入力してください。"],
        )
    if parsed_wp_url.scheme not in {"http", "https"} or not parsed_wp_url.netloc:
        raise _connection_error(
            "WordPress URLはhttpまたはhttpsから入力してください。",
            "WordPress URLの形式が正しくありません。",
            evidence=[f"入力値: {normalized_wp_url}"],
            suggestions=[
                "https://example.com のようにサイトのトップURLを入力してください。",
                "URLの末尾に /wp-json を付けないでください。",
            ],
        )
    if not username or not app_password:
        missing = [
            name
            for name, value in (
                ("WP_USERNAME", username),
                ("WP_APP_PASSWORD", app_password),
            )
            if not value
        ]
        raise _connection_error(
            "WP_USERNAMEまたはWP_APP_PASSWORDが設定されていません。",
            "Renderまたはローカル環境へ必要な認証情報が渡されていません。",
            evidence=[f"未設定: {', '.join(missing)}"],
            suggestions=[
                "Render DashboardのEnvironmentへ不足している環境変数を設定してください。",
                "Renderでは保存後にSave and deployを実行してください。",
            ],
        )

    return normalized_wp_url, username, app_password


def _response_details(response: requests.Response) -> dict[str, str]:
    raw_content_type = response.headers.get("content-type", "不明")
    content_type = (
        raw_content_type.split(";", 1)[0]
        if isinstance(raw_content_type, str)
        else "不明"
    )
    raw_final_url = getattr(response, "url", "")
    final_url = raw_final_url if isinstance(raw_final_url, str) else "不明"
    final_url = final_url or "不明"
    history = getattr(response, "history", []) or []
    if not isinstance(history, (list, tuple)):
        history = []
    details = {
        "HTTPステータス": str(response.status_code),
        "応答形式": content_type,
        "最終URL": final_url,
        "リダイレクト回数": str(len(history)),
    }

    server = response.headers.get("server")
    if isinstance(server, str) and server:
        details["応答サーバー"] = server[:100]

    return details


def _runtime_details(username: str, app_password: str) -> dict[str, str]:
    has_literal_quotes = any(
        value.startswith(("'", '"')) or value.endswith(("'", '"'))
        for value in (username, app_password)
    )
    return {
        "実行環境": (
            "Render"
            if os.getenv("RENDER", "").lower() == "true"
            else "ローカルまたはその他"
        ),
        "WP_USERNAME": "設定済み",
        "WP_APP_PASSWORD": "設定済み",
        "パスワード内の空白": "あり" if " " in app_password else "なし",
        "値に含まれる引用符": "検出" if has_literal_quotes else "なし",
    }


def _safe_json(response: requests.Response) -> dict | list | None:
    try:
        return response.json()
    except (requests.JSONDecodeError, ValueError):
        return None


def _wordpress_error_evidence(payload: dict | list | None) -> list[str]:
    if not isinstance(payload, dict):
        return []

    evidence = []
    code = payload.get("code")
    message = payload.get("message")
    if code:
        evidence.append(f"WordPressエラーコード: {str(code)[:120]}")
    if message:
        evidence.append(f"WordPress応答: {str(message)[:300]}")
    return evidence


def _redirect_evidence(response: requests.Response) -> list[str]:
    history = getattr(response, "history", []) or []
    if not history:
        return []

    locations = []
    for item in history[-3:]:
        location = item.headers.get("location")
        if location:
            locations.append(location[:200])
    return [f"リダイレクト先: {' → '.join(locations)}"] if locations else []


def test_wordpress_connection(wp_url: str) -> dict:
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
        raise _connection_error(
            "WordPressへの接続がタイムアウトしました。",
            "WordPressサーバーが30秒以内に応答しませんでした。",
            evidence=[f"確認先: {endpoint}"],
            suggestions=[
                "WordPressサーバーとCDNの稼働状況を確認してください。",
                "国外アクセス制限やRenderからの通信制限を確認してください。",
            ],
        ) from exc
    except SSLError as exc:
        raise _connection_error(
            "WordPressとのSSL通信に失敗しました。",
            "SSL証明書の期限切れ、ホスト名不一致、または証明書チェーンの問題です。",
            evidence=[f"確認先: {endpoint}"],
            suggestions=[
                "WordPressサイトのSSL証明書を確認してください。",
                "WP_URLが証明書に登録されたドメインと一致しているか確認してください。",
            ],
        ) from exc
    except TooManyRedirects as exc:
        raise _connection_error(
            "WordPressへの接続がリダイレクトを繰り返しました。",
            "WordPress URL、HTTPS化、またはCDNのリダイレクト設定が循環しています。",
            evidence=[f"確認先: {endpoint}"],
            suggestions=[
                "httpとhttps、www有無の転送設定を確認してください。",
                "WordPressアドレスとサイトアドレスを確認してください。",
            ],
        ) from exc
    except ProxyError as exc:
        raise _connection_error(
            "WordPressへの接続がプロキシで失敗しました。",
            "RenderとWordPressの間にあるプロキシまたはCDNが通信を拒否しました。",
            evidence=[f"確認先: {endpoint}"],
            suggestions=[
                "Cloudflare、WAF、ホスティング側のアクセス制限を確認してください。",
                "RenderのアウトバウンドIP範囲が拒否されていないか確認してください。",
            ],
        ) from exc
    except ConnectionError as exc:
        error_text = str(exc).lower()
        dns_failed = any(
            marker in error_text
            for marker in ("name resolution", "getaddrinfo", "nodename nor servname")
        )
        cause = (
            "WordPressのドメイン名をDNSで解決できませんでした。"
            if dns_failed
            else "WordPressサーバーとのネットワーク接続を確立できませんでした。"
        )
        raise _connection_error(
            "WordPressへ接続できませんでした。",
            cause,
            evidence=[f"確認先: {endpoint}"],
            suggestions=[
                "WP_URLのドメイン名とDNS設定を確認してください。",
                "WordPress側のファイアウォールや国外アクセス制限を確認してください。",
                "RenderのアウトバウンドIP範囲が拒否されていないか確認してください。",
            ],
        ) from exc
    except requests.RequestException as exc:
        raise _connection_error(
            "WordPressへの接続要求に失敗しました。",
            "HTTPリクエストを正常に送信できませんでした。",
            evidence=[f"確認先: {endpoint}"],
            suggestions=["URL、プロキシ、ネットワーク設定を確認してください。"],
        ) from exc

    details = {
        **_runtime_details(username, app_password),
        **_response_details(response),
    }
    payload = _safe_json(response)
    wordpress_evidence = _wordpress_error_evidence(payload)
    redirect_evidence = _redirect_evidence(response)
    final_url = details["最終URL"].lower()
    content_type = details["応答形式"].lower()

    if "wp-login.php" in final_url:
        raise _connection_error(
            "WordPress REST APIではなくログイン画面へ転送されました。",
            "セキュリティ設定、Basic認証、またはログイン強制機能がREST APIを遮断しています。",
            evidence=redirect_evidence,
            suggestions=[
                "REST APIの /wp-json/wp/v2/users/me をログイン画面へ転送しないよう設定してください。",
                "WordPressのセキュリティプラグインとサーバーBasic認証を確認してください。",
            ],
            details=details,
        )

    if response.status_code == 401:
        raise _connection_error(
            "WordPressの認証に失敗しました。",
            "ユーザー名またはアプリケーションパスワードが拒否されたか、AuthorizationヘッダーがWordPressへ届いていません。",
            evidence=wordpress_evidence + redirect_evidence,
            suggestions=[
                "WP_USERNAMEがWordPressのログインユーザー名と一致するか確認してください。",
                "通常のログインパスワードではなくアプリケーションパスワードを設定してください。",
                "Renderの環境変数を保存後、Save and deployを実行してください。",
                "CDN、プロキシ、サーバーがAuthorizationヘッダーを削除していないか確認してください。",
            ],
            details=details,
        )

    if response.status_code == 403:
        is_json_response = "json" in content_type or isinstance(payload, dict)
        cause = (
            "WordPressまたはセキュリティプラグインが、このユーザーのREST APIアクセスを拒否しました。"
            if is_json_response
            else "WordPressの手前にあるWAF、CDN、国外アクセス制限、またはIP制限がRenderからの通信を拒否した可能性が高いです。"
        )
        raise _connection_error(
            "WordPressへのアクセスが拒否されました。",
            cause,
            evidence=wordpress_evidence + redirect_evidence,
            suggestions=[
                "Cloudflare、Wordfence、SiteGuard、サーバーの国外アクセス制限を確認してください。",
                "Render DashboardのConnect → Outboundに表示されるIP範囲を許可してください。",
                "REST APIとアプリケーションパスワードが無効化されていないか確認してください。",
            ],
            details=details,
        )

    if response.status_code == 404:
        raise _connection_error(
            "WordPress REST APIが見つかりません。",
            "WP_URLがWordPressの設置先と異なるか、REST APIのURLがサーバーまたはプラグインで無効化されています。",
            evidence=wordpress_evidence + redirect_evidence,
            suggestions=[
                "WP_URLにはWordPressサイトのトップURLを指定し、/wp-jsonを付けないでください。",
                "ブラウザで /wp-json/ がJSONを返すか確認してください。",
                "パーマリンク設定とREST API制限プラグインを確認してください。",
            ],
            details=details,
        )

    if response.status_code == 429:
        raise _connection_error(
            "WordPressへの接続回数が制限されました。",
            "CDN、WAF、またはWordPress側のレート制限が発動しています。",
            evidence=wordpress_evidence,
            suggestions=[
                "時間を置いて再実行してください。",
                "セキュリティ機能のレート制限とRenderのIP許可設定を確認してください。",
            ],
            details=details,
        )

    if response.status_code >= 500:
        raise _connection_error(
            f"WordPressがサーバーエラーを返しました（HTTP {response.status_code}）。",
            "WordPress、PHP、Webサーバー、CDNのいずれかで内部エラーが発生しています。",
            evidence=wordpress_evidence,
            suggestions=[
                "WordPressとサーバーのエラーログを確認してください。",
                "プラグイン競合、PHPエラー、CDN障害を確認してください。",
            ],
            details=details,
        )

    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        raise _connection_error(
            f"WordPressがエラーを返しました（HTTP {response.status_code}）。",
            "WordPressまたは中継サーバーが接続テストを正常に処理できませんでした。",
            evidence=wordpress_evidence + redirect_evidence,
            suggestions=[
                "HTTPステータスとWordPressエラーコードをもとにサーバー設定を確認してください。"
            ],
            details=details,
        ) from exc

    user = payload
    if user is None:
        likely_html = "html" in content_type
        cause = (
            "REST APIの代わりにHTMLページが返されています。WAF、CDN、ログイン画面、またはサーバー認証が割り込んでいる可能性があります。"
            if likely_html
            else "WordPress REST APIからJSON以外の応答が返されました。"
        )
        raise _connection_error(
            "WordPressから正しいJSON応答を取得できませんでした。",
            cause,
            evidence=redirect_evidence,
            suggestions=[
                "最終URLをブラウザで開き、REST APIのJSONが表示されるか確認してください。",
                "Cloudflare、WAF、サーバーBasic認証、メンテナンス画面を確認してください。",
            ],
            details=details,
        )

    if not isinstance(user, dict):
        raise _connection_error(
            "WordPressからユーザー情報を取得できませんでした。",
            "REST APIは応答しましたが、現在ユーザーの情報ではないJSONが返されました。",
            suggestions=[
                "REST APIを書き換えるプラグインやキャッシュ設定を確認してください。"
            ],
            details=details,
        )

    capabilities = user.get("capabilities")
    if not isinstance(capabilities, dict):
        raise _connection_error(
            "認証には成功しましたが、下書き作成権限を確認できませんでした。",
            "ユーザー情報にcapabilitiesが含まれていません。REST APIの応答をプラグインやフィルターが変更している可能性があります。",
            evidence=[f"認証ユーザー: {str(user.get('name') or username)[:100]}"],
            suggestions=[
                "ユーザー情報を変更するセキュリティプラグインやREST APIフィルターを確認してください。",
                "対象ユーザーが投稿者以上の権限を持つかWordPress管理画面で確認してください。",
            ],
            details=details,
        )
    if not capabilities.get("edit_posts"):
        raise _connection_error(
            "認証には成功しましたが、このユーザーには記事の下書きを作成する権限がありません。",
            "認証ユーザーのedit_posts権限が無効です。",
            evidence=[
                f"認証ユーザー: {str(user.get('name') or username)[:100]}",
                "edit_posts: false",
            ],
            suggestions=[
                "WordPressで対象ユーザーを投稿者、編集者、管理者など投稿可能な権限へ変更してください。"
            ],
            details=details,
        )

    return {
        "display_name": str(user.get("name") or username),
        "username": str(user.get("username") or username),
        "site_url": normalized_wp_url,
        "cause": "接続情報、REST API認証、下書き作成権限に問題は見つかりませんでした。",
        "evidence": [
            f"HTTP {response.status_code}でWordPress REST APIが応答しました。",
            "アプリケーションパスワードで現在ユーザーを取得できました。",
            "edit_posts権限が有効です。",
        ],
        "details": details,
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
