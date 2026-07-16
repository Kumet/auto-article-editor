import json
import os
from pathlib import Path
from urllib.parse import urlparse

from app.default_template import DEFAULT_TEMPLATE

BASE_DIR = Path(__file__).resolve().parent.parent


def _settings_path() -> Path:
    configured_path = os.getenv("APP_SETTINGS_PATH")
    return Path(configured_path) if configured_path else BASE_DIR / "data" / "settings.json"


def validate_wp_url(wp_url: str) -> str:
    """Normalize and validate a WordPress site URL."""
    normalized = wp_url.strip().rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("WordPress URLは http または https から入力してください。")
    return normalized


def _environment_wp_url() -> str:
    wp_url = os.getenv("WP_URL", "").strip()
    if not wp_url:
        return ""

    try:
        return validate_wp_url(wp_url)
    except ValueError:
        return ""


def _default_settings() -> dict:
    return {
        "default_template": (
            os.getenv("DEFAULT_ARTICLE_TEMPLATE", "").strip() or DEFAULT_TEMPLATE
        ),
        "wp_url": _environment_wp_url(),
    }


def settings_are_ephemeral() -> bool:
    """Return whether UI changes are stored on an ephemeral filesystem."""
    return os.getenv("APP_SETTINGS_EPHEMERAL", "").lower() == "true"


def load_settings() -> dict:
    """Load locally persisted application settings."""
    settings = _default_settings()
    path = _settings_path()
    if not path.exists():
        return settings

    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return settings

    if isinstance(stored, dict):
        template = stored.get("default_template")
        wp_url = stored.get("wp_url")
        if isinstance(template, str) and template.strip():
            settings["default_template"] = template
        if isinstance(wp_url, str):
            settings["wp_url"] = wp_url.rstrip("/")

    return settings


def save_settings(default_template: str, wp_url: str) -> dict:
    """Persist application settings atomically as a local JSON file."""
    normalized_template = default_template.strip()
    if not normalized_template:
        raise ValueError("デフォルトの記事の型を入力してください。")

    settings = {
        "default_template": normalized_template,
        "wp_url": validate_wp_url(wp_url),
    }
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)
    return settings
