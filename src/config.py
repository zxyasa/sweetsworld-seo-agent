"""Configuration management for SEO automation agent."""
from __future__ import annotations

import logging
import logging.handlers
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv


def setup_logging(log_dir: Optional[Path] = None) -> logging.Logger:
    """Configure file + stream logging for the SEO agent.

    Call once at process startup (run_mvp.py main). All other modules
    use logging.getLogger(__name__) and inherit this configuration.
    """
    root_logger = logging.getLogger()
    if root_logger.handlers:
        # Already configured (e.g., called twice) — skip
        return root_logger

    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Stream handler — INFO+ to stdout (same visibility as before)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # File handler — DEBUG+ to rotating log file
    if log_dir is None:
        log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "seo_agent.log"

    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    return root_logger


def _find_env_file() -> Path:
    """Find .env file in project root."""
    current = Path(__file__).parent.parent / ".env"
    if current.exists():
        return current

    parent = Path(__file__).parent.parent.parent / ".env"
    if parent.exists():
        return parent

    return current


def _clean_env_value(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip().strip('"').strip("'")


def _get_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(int(raw), minimum)
    except ValueError:
        return default


def _get_list_env(name: str, default: str = "") -> List[str]:
    raw = _clean_env_value(name, default)
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return list(dict.fromkeys(values))


def _resolve_project_path(path_value: str, fallback: str) -> str:
    cleaned = (path_value or fallback).strip().strip('"').strip("'") or fallback
    candidate = Path(cleaned)
    if candidate.is_absolute():
        return str(candidate)
    project_root = Path(__file__).parent.parent
    return str(project_root / candidate)


# Load environment variables from .env file
env_path = _find_env_file()
load_dotenv(dotenv_path=env_path)


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    wp_base_url: str
    wp_username: str
    wp_app_password: str
    telegram_bot_token: str
    telegram_chat_id: str
    openai_api_key: str
    openai_model: str
    use_ai_generation: bool
    gsc_property_url: str
    gsc_credentials_file: str
    use_gsc_data: bool
    seo_run_mode: str
    daily_limit: int
    state_file: str
    auto_publish_created_posts: bool
    auto_generate_topics: bool
    topic_generation_source: str
    topic_target_pending: int
    topic_seeds: List[str]
    wp_guide_category_slug: str
    wp_guide_category_name: str
    wp_occasion_category_slug: str
    wp_occasion_category_name: str
    wp_landing_category_slug: str
    wp_landing_category_name: str
    wp_category_page_category_slug: str
    wp_category_page_category_name: str


def get_site_collection_urls(base_url: str) -> dict:
    """Return standard on-site collection URLs derived from WP_BASE_URL.

    Use this instead of hardcoding sweetsworld.com.au paths in generator modules.
    Keys are stable identifiers; values are absolute URLs.
    """
    b = base_url.rstrip("/")
    return {
        "candy": f"{b}/candy/",
        "chocolate": f"{b}/chocolate/",
        "wholesale": f"{b}/wholesale-candy-australia/",
        "sour_lollies": f"{b}/candy/sour-lollies/",
        "american_candy": f"{b}/candy/american-candy/",
        "japanese_candy": f"{b}/candy/japanese-candy/",
    }


def get_settings() -> Settings:
    """Load and validate settings from environment variables."""
    if not env_path.exists():
        raise RuntimeError(
            f"ERROR: .env file not found at: {env_path}\n"
            f"   - Copy .env.example to .env: cp .env.example .env\n"
            f"   - Fill in your WordPress credentials\n"
            f"   - Get Application Password from: Users -> Profile -> Application Passwords"
        )

    wp_base_url = _clean_env_value("WP_BASE_URL")
    wp_username = _clean_env_value("WP_USERNAME")
    wp_app_password = _clean_env_value("WP_APP_PASSWORD")

    telegram_bot_token = _clean_env_value("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = _clean_env_value("TELEGRAM_CHAT_ID")

    openai_api_key = _clean_env_value("OPENAI_API_KEY")
    openai_model = _clean_env_value("OPENAI_MODEL", "gpt-4o") or "gpt-4o"
    use_ai_generation = _get_bool_env("USE_AI_GENERATION", False)

    gsc_property_url = _clean_env_value("GSC_PROPERTY_URL")
    gsc_credentials_file = _resolve_project_path(
        _clean_env_value("GSC_CREDENTIALS_FILE", "gsc_credentials.json"),
        "gsc_credentials.json",
    )
    use_gsc_data = _get_bool_env("USE_GSC_DATA", False)

    seo_run_mode = _clean_env_value("SEO_RUN_MODE", "batch").lower() or "batch"
    if seo_run_mode not in {"batch", "daily"}:
        seo_run_mode = "batch"

    daily_limit = _get_int_env("DAILY_LIMIT", 1, minimum=1)
    state_file = _resolve_project_path(
        _clean_env_value("SEO_STATE_FILE", "data/seo_daily_state.json"),
        "data/seo_daily_state.json",
    )
    auto_publish_created_posts = _get_bool_env("AUTO_PUBLISH_CREATED_POSTS", False)
    auto_generate_topics = _get_bool_env("AUTO_GENERATE_TOPICS", False)

    topic_generation_source = _clean_env_value("TOPIC_GENERATION_SOURCE", "auto").lower() or "auto"
    if topic_generation_source not in {"auto", "seed", "gsc"}:
        topic_generation_source = "auto"

    topic_target_pending = _get_int_env("TOPIC_TARGET_PENDING", 5, minimum=1)
    topic_seeds = _get_list_env("TOPIC_SEEDS", "candy")

    wp_guide_category_slug = _clean_env_value("WP_GUIDE_CATEGORY_SLUG", "candy-guides") or "candy-guides"
    wp_guide_category_name = _clean_env_value("WP_GUIDE_CATEGORY_NAME", "Candy Guides") or "Candy Guides"
    wp_occasion_category_slug = _clean_env_value("WP_OCCASION_CATEGORY_SLUG", wp_guide_category_slug) or wp_guide_category_slug
    wp_occasion_category_name = _clean_env_value("WP_OCCASION_CATEGORY_NAME", wp_guide_category_name) or wp_guide_category_name
    wp_landing_category_slug = _clean_env_value("WP_LANDING_CATEGORY_SLUG", "where-to-buy") or "where-to-buy"
    wp_landing_category_name = _clean_env_value("WP_LANDING_CATEGORY_NAME", "Where to Buy") or "Where to Buy"
    wp_category_page_category_slug = _clean_env_value("WP_CATEGORY_PAGE_CATEGORY_SLUG", "products") or "products"
    wp_category_page_category_name = _clean_env_value("WP_CATEGORY_PAGE_CATEGORY_NAME", "Products") or "Products"

    missing_fields = []
    if not wp_base_url:
        missing_fields.append("WP_BASE_URL")
    if not wp_username:
        missing_fields.append("WP_USERNAME")
    if not wp_app_password:
        missing_fields.append("WP_APP_PASSWORD")

    if missing_fields:
        raise RuntimeError(
            f"ERROR: Missing required configuration in .env file:\n"
            f"   - {', '.join(missing_fields)}\n\n"
            f"   Please edit {env_path} and fill in:\n"
            f"   WP_BASE_URL=\"https://sweetsworld.com.au\"\n"
            f"   WP_USERNAME=\"your_username\"\n"
            f"   WP_APP_PASSWORD=\"xxxx xxxx xxxx xxxx\"\n\n"
            f"   Get Application Password from:\n"
            f"   WordPress Admin -> Users -> Profile -> Application Passwords"
        )

    if not wp_base_url.startswith(("http://", "https://")):
        raise RuntimeError(
            f"ERROR: Invalid WP_BASE_URL: {wp_base_url}\n"
            f"   - Must start with http:// or https://\n"
            f"   - Example: https://sweetsworld.com.au"
        )

    if " " not in wp_app_password:
        print(
            f"WARN: WP_APP_PASSWORD might be incorrect\n"
            f"   - Application Password usually has spaces (e.g., 'xxxx xxxx xxxx xxxx')\n"
            f"   - Your password: '{wp_app_password[:4]}****'\n"
        )

    return Settings(
        wp_base_url=wp_base_url,
        wp_username=wp_username,
        wp_app_password=wp_app_password,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        use_ai_generation=use_ai_generation,
        gsc_property_url=gsc_property_url,
        gsc_credentials_file=gsc_credentials_file,
        use_gsc_data=use_gsc_data,
        seo_run_mode=seo_run_mode,
        daily_limit=daily_limit,
        state_file=state_file,
        auto_publish_created_posts=auto_publish_created_posts,
        auto_generate_topics=auto_generate_topics,
        topic_generation_source=topic_generation_source,
        topic_target_pending=topic_target_pending,
        topic_seeds=topic_seeds,
        wp_guide_category_slug=wp_guide_category_slug,
        wp_guide_category_name=wp_guide_category_name,
        wp_occasion_category_slug=wp_occasion_category_slug,
        wp_occasion_category_name=wp_occasion_category_name,
        wp_landing_category_slug=wp_landing_category_slug,
        wp_landing_category_name=wp_landing_category_name,
        wp_category_page_category_slug=wp_category_page_category_slug,
        wp_category_page_category_name=wp_category_page_category_name,
    )
