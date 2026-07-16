from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from readability import Document


REQUEST_TIMEOUT_SECONDS = 20
MAX_ARTICLE_CHARS = 60_000
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)


class ArticleExtractionError(RuntimeError):
    """Raised when an article cannot be downloaded or parsed."""


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ArticleExtractionError("http または https の記事URLを入力してください。")


def _clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript", "svg"]):
        element.decompose()

    lines = (line.strip() for line in soup.get_text("\n").splitlines())
    return "\n".join(line for line in lines if line)


def extract_article(url: str) -> dict:
    """Download an article and return its title and readable plain-text body."""
    normalized_url = url.strip()
    _validate_url(normalized_url)

    try:
        response = requests.get(
            normalized_url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ArticleExtractionError(
            "記事を取得できませんでした。URLと公開状態を確認してください。"
        ) from exc

    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding

    document = Document(response.text)
    title = document.short_title().strip()
    content = _clean_text(document.summary())

    if not title:
        page = BeautifulSoup(response.text, "html.parser")
        title = page.title.get_text(strip=True) if page.title else "無題の記事"

    if len(content) < 100:
        page = BeautifulSoup(response.text, "html.parser")
        body = page.body or page
        content = _clean_text(str(body))

    if not content:
        raise ArticleExtractionError("記事本文を抽出できませんでした。")

    return {
        "title": title,
        "content": content[:MAX_ARTICLE_CHARS],
    }
