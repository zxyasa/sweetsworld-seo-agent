"""SiteContext — immutable per-site configuration object.

Load once at process startup via load_site_context(site_id).
Pass the resulting SiteContext through the entire call chain.
Never use global variables or os.environ for site-specific config.

Usage:
    ctx = load_site_context("sweetsworld")
    db  = ctx.db          # SiteDB bound to this site
    wp  = make_wp_client(ctx)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from site_db import SiteDB

logger = logging.getLogger(__name__)

# Root of all site packages, relative to this file (src/).
_SITES_ROOT = Path(__file__).parent.parent / "sites"


@dataclass(frozen=True)
class SiteContext:
    """Immutable site configuration. frozen=True prevents accidental mutation."""

    # ── Identity ──────────────────────────────────────────────────────────────
    site_id:      str
    display_name: str
    base_url:     str       # no trailing slash
    site_dir:     Path      # absolute path to sites/<site_id>/

    # ── Content generation (injected into every Claude prompt) ────────────────
    niche:       str        # e.g. "ecommerce_candy" | "local_business_hub"
    audience:    str        # e.g. "Australian candy lovers"
    brand_voice: str        # e.g. "fun, friendly, enthusiastic"
    faq_context: str        # "candy_blog" | "business"
    language:    str        # "en-AU" | "en-US"

    # ── Catalog ───────────────────────────────────────────────────────────────
    catalog_type: str       # "products" | "services"
    catalog_path: Path      # absolute path to products.json / services.json

    # ── Collection paths (site-specific URL slugs for internal links) ─────────
    collection_urls: dict[str, str]   # {"candy": "https://…/candy/", ...}

    # ── WordPress category mappings ───────────────────────────────────────────
    wp_categories: dict[str, dict[str, str]]  # page_type → {slug, name, id?}

    # ── Database ──────────────────────────────────────────────────────────────
    db: SiteDB              # bound to sites/<site_id>/data/site.db

    # ── WordPress credentials ─────────────────────────────────────────────────
    wp_username:    str
    wp_password:    str

    # ── External API credentials ──────────────────────────────────────────────
    anthropic_api_key:       str
    gsc_credentials_file:    Path        # JSON key file
    indexing_key_file:       Path | None # None = indexing disabled
    telegram_bot_token:      str
    telegram_chat_id:        str

    # ── Publish behaviour ─────────────────────────────────────────────────────
    daily_publish_limit:   int
    indexing_api_enabled:  bool
    auto_publish:          bool

    # ── GSC property ──────────────────────────────────────────────────────────
    gsc_property_url: str

    # ── Content defaults ──────────────────────────────────────────────────────
    default_category_hint: str  # fallback for topics missing category_hint

    # ── Per-site prompt customisation (optional, from site.json → "prompt_config") ──
    # All keys are optional; missing keys fall back to OpenAIGenerator defaults.
    # Supported keys:
    #   target_audience      — replaces "Australian consumers and businesses buying candy/confectionery"
    #   language_instruction — replaces "English (Australian English spelling and style)"
    #   tone_style           — replaces the Tone & Style bullet list
    #   extra_instructions   — appended as an extra mandatory block at the end of the prompt
    #   word_count           — e.g. "1200-1500" (default)
    prompt_config: dict  # free-form overrides forwarded to OpenAIGenerator


def load_site_context(site_id: str, sites_root: Path | None = None) -> SiteContext:
    """Load and validate a SiteContext from sites/<site_id>/.

    Reads:
      sites/<site_id>/site.json  — structural config (committed to git)
      sites/<site_id>/.env       — credentials (gitignored)

    Raises:
      FileNotFoundError  — site directory or site.json missing
      ValueError         — site_id mismatch or missing required credential
      KeyError           — required env var not present in .env
    """
    root = sites_root or _SITES_ROOT
    site_dir = root / site_id

    if not site_dir.is_dir():
        raise FileNotFoundError(
            f"Site directory not found: {site_dir}\n"
            f"  Create it with: mkdir -p {site_dir} && touch {site_dir}/site.json"
        )

    cfg_path = site_dir / "site.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"site.json missing: {cfg_path}")

    cfg: dict[str, Any] = json.loads(cfg_path.read_text())

    # ── Guard: directory name must match declared site_id ─────────────────────
    if cfg.get("site_id") != site_id:
        raise ValueError(
            f"site.json declares site_id={cfg.get('site_id')!r} "
            f"but was loaded as {site_id!r}. Fix site.json or the --site argument."
        )

    # ── Load credentials from site-local .env (does NOT pollute os.environ) ──
    # Falls back to os.environ for shared keys (e.g. ANTHROPIC_API_KEY).
    import os as _os
    env_path = site_dir / ".env"
    env: dict[str, str | None] = dotenv_values(env_path) if env_path.exists() else {}

    def require_env(key: str) -> str:
        v = (env.get(key) or _os.environ.get(key) or "").strip()
        if not v:
            raise KeyError(
                f"[{site_id}] Required credential missing: {key}\n"
                f"  Add it to {env_path}"
            )
        return v

    def optional_env(key: str, default: str = "") -> str:
        return (env.get(key) or _os.environ.get(key) or default).strip()

    # ── Catalog path ──────────────────────────────────────────────────────────
    content_cfg = cfg.get("content", {})
    catalog_file = content_cfg.get("catalog_file", "products.json")
    catalog_path = site_dir / catalog_file
    if not catalog_path.exists():
        logger.warning("[%s] Catalog file not found: %s", site_id, catalog_path)

    # ── Collection URLs (expand base_url placeholder) ─────────────────────────
    base_url = cfg["base_url"].rstrip("/")
    raw_collections = cfg.get("collection_paths", {})
    collection_urls = {
        k: f"{base_url}{v}" if v.startswith("/") else v
        for k, v in raw_collections.items()
    }

    # ── Indexing API key ──────────────────────────────────────────────────────
    idx_key_rel = cfg.get("indexing_key_file")
    indexing_key_file: Path | None = None
    if idx_key_rel:
        indexing_key_file = site_dir / idx_key_rel
        if not indexing_key_file.exists():
            logger.warning("[%s] Indexing key file not found: %s", site_id, indexing_key_file)
            indexing_key_file = None

    # ── GSC credentials ───────────────────────────────────────────────────────
    gsc_cfg = cfg.get("gsc", {})
    gsc_creds_rel = optional_env(gsc_cfg.get("env_credentials", "GSC_CREDENTIALS_FILE"), "")
    gsc_credentials_file = site_dir / gsc_creds_rel if gsc_creds_rel else site_dir / "gsc_credentials.json"

    wp_cfg = cfg.get("wp", {})
    tg_cfg = cfg.get("telegram", {})
    publish_cfg = cfg.get("publish", {})

    ctx = SiteContext(
        site_id      = site_id,
        display_name = cfg["display_name"],
        base_url     = base_url,
        site_dir     = site_dir,

        niche        = cfg.get("niche", ""),
        audience     = cfg.get("audience", ""),
        brand_voice  = cfg.get("brand_voice", ""),
        faq_context  = content_cfg.get("faq_context", "business"),
        language     = cfg.get("language", "en-AU"),

        catalog_type = content_cfg.get("catalog_type", "products"),
        catalog_path = catalog_path,
        collection_urls = collection_urls,
        wp_categories   = cfg.get("wp_categories", {}),

        db = SiteDB(site_dir),

        wp_username = require_env(wp_cfg.get("env_username", "WP_USERNAME")),
        wp_password = require_env(wp_cfg.get("env_password", "WP_APP_PASSWORD")),

        anthropic_api_key    = require_env("ANTHROPIC_API_KEY"),
        gsc_credentials_file = gsc_credentials_file,
        indexing_key_file    = indexing_key_file,
        telegram_bot_token   = require_env(tg_cfg.get("env_bot_token", "TELEGRAM_BOT_TOKEN")),
        telegram_chat_id     = require_env(tg_cfg.get("env_chat_id", "TELEGRAM_CHAT_ID")),

        gsc_property_url      = gsc_cfg.get("property", base_url + "/"),
        daily_publish_limit   = publish_cfg.get("daily_limit", 1),
        indexing_api_enabled  = publish_cfg.get("indexing_api_enabled", False),
        auto_publish          = publish_cfg.get("auto_publish", True),

        default_category_hint = content_cfg.get("default_category_hint", "Confectionery"),
        prompt_config = cfg.get("prompt_config", {}),
    )

    logger.info(
        "[%s] SiteContext loaded — %s | catalog=%s(%s) | limit=%d/day",
        site_id, base_url, catalog_type := content_cfg.get("catalog_type", "products"),
        catalog_file, publish_cfg.get("daily_limit", 1),
    )
    return ctx


def list_sites(sites_root: Path | None = None) -> list[str]:
    """Return site_ids of all registered sites (directories with site.json)."""
    root = sites_root or _SITES_ROOT
    if not root.exists():
        return []
    return sorted(
        d.name for d in root.iterdir()
        if d.is_dir() and (d / "site.json").exists()
    )


def apply_site_context_env(ctx: SiteContext) -> None:
    """Expose site-specific settings through environment variables.

    This keeps legacy code paths that still call get_settings() working with
    the active site instead of falling back to the root sweetsworld defaults.
    """
    import os

    os.environ["WP_BASE_URL"] = ctx.base_url
    os.environ["WP_USERNAME"] = ctx.wp_username
    os.environ["WP_APP_PASSWORD"] = ctx.wp_password
    os.environ["TELEGRAM_BOT_TOKEN"] = ctx.telegram_bot_token
    os.environ["TELEGRAM_CHAT_ID"] = ctx.telegram_chat_id

    # Bridge token for RankMath SEO meta writes (wp-seo-meta.php)
    _site_env_path = _SITES_ROOT / ctx.site_id / ".env"
    if _site_env_path.exists():
        _site_env = dotenv_values(_site_env_path)
        _bridge_token = (_site_env.get("WP_SEO_BRIDGE_TOKEN") or "").strip()
        if _bridge_token:
            os.environ["WP_SEO_BRIDGE_TOKEN"] = _bridge_token

    if ctx.gsc_property_url:
        os.environ["GSC_PROPERTY_URL"] = ctx.gsc_property_url

    if ctx.gsc_credentials_file.exists():
        os.environ["GSC_CREDENTIALS_FILE"] = str(ctx.gsc_credentials_file)
        os.environ["USE_GSC_DATA"] = "true"
    else:
        os.environ["GSC_CREDENTIALS_FILE"] = ""
        os.environ["USE_GSC_DATA"] = "false"
