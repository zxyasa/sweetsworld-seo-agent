# Deterministic product selection for MVP pilot pages.
from __future__ import annotations

import html
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

STOPWORDS = {
    "alternatives",
    "australia",
    "best",
    "bulk",
    "buy",
    "buying",
    "candy",
    "check",
    "cheap",
    "does",
    "for",
    "gelatine",
    "guide",
    "how",
    "ingredients",
    "is",
    "lollies",
    "online",
    "options",
    "page",
    "the",
    "to",
    "what",
    "where",
    "why",
}

WEAK_TOKENS = {
    "american",
    "bars",
    "birthday",
    "box",
    "bulk",
    "candy",
    "category",
    "chocolate",
    "christmas",
    "easter",
    "gift",
    "grocery",
    "gummy",
    "guide",
    "halal",
    "halloween",
    "ingredients",
    "japanese",
    "kids",
    "landing",
    "lollies",
    "movie",
    "night",
    "occasion",
    "page",
    "party",
    "road",
    "sour",
    "trip",
    "vegan",
    "valentines",
    "white",
}

RULE_TOKENS = {
    "american": ["american"],
    "birthday": ["birthday", "kids", "gummy"],
    "chocolate": ["chocolate"],
    "christmas": ["christmas", "gift"],
    "easter": ["easter", "gift"],
    "gift box": ["gift", "box"],
    "gummy": ["gummy"],
    "halloween": ["halloween", "sour", "gummy"],
    "japanese": ["japanese", "japan", "pocky", "dagashi", "kracie", "meiji"],
    "kids": ["kids", "gummy", "chocolate"],
    "movie night": ["movie", "chocolate", "gummy", "share"],
    "party": ["party", "share", "gummy"],
    "road trip": ["road", "gummy", "share"],
    "sour": ["sour"],
    "valentines": ["valentines", "gift", "chocolate"],
}

# Minimal built-in fallback so behavior remains stable if the data file is missing.
DEFAULT_SUBSTITUTE_HINTS = {
    "fantales": ["milk chocolate chewy caramel", "chewy caramel"],
}

FAMILY_FALLBACK_PHRASES = {
    "caramel": ["milk chocolate chewy caramel", "chewy caramel", "caramel"],
    "chewy": ["chewy caramel", "chews"],
    "chews": ["chewy caramel", "chews"],
    "chocolate": ["chocolate"],
    "fudge": ["fudge", "caramel fudge"],
    "gummy": ["gummy", "gummies", "jelly"],
    "gummies": ["gummy", "gummies", "jelly"],
    "hard candy": ["hard candy"],
    "jelly": ["jelly", "gummy"],
    "licorice": ["licorice"],
    "marshmallow": ["marshmallow"],
    "mint": ["mint", "mint chew"],
    "sherbet": ["sherbet"],
    "sour": ["sour"],
    "toffee": ["toffee", "caramel"],
}

CATEGORY_FALLBACK_PHRASES = {
    "american candy": ["american candy", "hard candy", "chocolate"],
    "candy & lollies": ["old fashion lollies", "chews", "caramel"],
    "chocolate bars": ["chocolate"],
    "gummy candy": ["gummy", "gummies"],
    "old fashion lollies": ["old fashion lollies", "caramel", "toffee"],
    "sour candy": ["sour"],
}

_SUBSTITUTE_HINTS_CACHE: Optional[Dict[str, List[str]]] = None


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def _normalize_word(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return f"{word[:-3]}y"
    if word.endswith("s") and len(word) > 4 and not word.endswith("ss"):
        return word[:-1]
    return word


def _normalize_phrase_text(value: Any) -> str:
    words = re.findall(r"[a-z0-9]+", _clean_text(value).lower())
    normalized = [_normalize_word(word) for word in words]
    return " ".join(normalized)


def _dedupe_preserve(items: List[str], limit: Optional[int] = None) -> List[str]:
    deduped: List[str] = []
    seen = set()
    for item in items:
        cleaned = _clean_text(item)
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
        if limit is not None and len(deduped) >= limit:
            break
    return deduped


def _substitute_hints_path() -> Path:
    return Path(__file__).resolve().parents[1] / 'data' / 'product_substitutions.json'


def _load_substitute_hints() -> Dict[str, List[str]]:
    global _SUBSTITUTE_HINTS_CACHE
    if _SUBSTITUTE_HINTS_CACHE is not None:
        return _SUBSTITUTE_HINTS_CACHE

    loaded: Dict[str, List[str]] = {}
    path = _substitute_hints_path()
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        payload = {}

    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized_key = _normalize_phrase_text(key)
            phrases = value if isinstance(value, list) else []
            normalized_phrases = _dedupe_preserve([_clean_text(item) for item in phrases if _clean_text(item)])
            if normalized_key and normalized_phrases:
                loaded[normalized_key] = normalized_phrases

    merged: Dict[str, List[str]] = {
        _normalize_phrase_text(key): _dedupe_preserve(list(value))
        for key, value in DEFAULT_SUBSTITUTE_HINTS.items()
    }
    merged.update(loaded)
    _SUBSTITUTE_HINTS_CACHE = merged
    return merged


def normalize_catalog(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add internal scoring fields (_name_text, _category_text, etc.) to raw product dicts.

    Must be called before select_products_for_topic(); load_product_catalog()
    calls this automatically, but callers using catalog_loader must call it
    explicitly.
    """
    products: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        product_name = _clean_text(row.get("product_name") or row.get("name"))
        product_url = _clean_text(row.get("url"))
        if not product_name or not product_url:
            continue
        # Skip draft products — their URLs are ?post_type=product&p=ID and don't resolve publicly
        if "?post_type=product&p=" in product_url:
            continue

        category = _clean_text(row.get("category", ""))
        tags = row.get("tags", [])
        categories = row.get("categories", [])
        if isinstance(tags, list):
            tag_text = " ".join(_clean_text(tag) for tag in tags if _clean_text(tag))
        else:
            tag_text = _clean_text(tags)
        if isinstance(categories, list):
            category_text = " ".join(_clean_text(cat) for cat in categories if _clean_text(cat))
        else:
            category_text = _clean_text(categories)

        description = _clean_text(row.get("description", ""))
        category_blob = f"{category} {category_text} {tag_text}".strip()
        normalized = {
            "product_name": product_name,
            "category": category,
            "description": description,
            "price": row.get("price", ""),
            "url": product_url,
            "image_url": _clean_text(row.get("image_url", "")),
            "_category_text": category_blob.lower(),
            "_name_text": product_name.lower(),
            "_normalized_name_text": _normalize_phrase_text(product_name),
            "_description_text": description.lower(),
            "_normalized_category_text": _normalize_phrase_text(category_blob),
            "_normalized_description_text": _normalize_phrase_text(description),
        }
        products.append(normalized)

    return products


def load_product_catalog(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []

    if isinstance(payload, dict):
        rows = payload.get("products", [])
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []

    return normalize_catalog(rows)


def _topic_seed_text(topic: Dict[str, str]) -> str:
    return " ".join(
        _clean_text(part)
        for part in [topic.get("primary_keyword", ""), topic.get("title", ""), topic.get("category_hint", "")]
        if _clean_text(part)
    )


def _topic_tokens(topic: Dict[str, str]) -> List[str]:
    haystack = _topic_seed_text(topic).lower() + " " + _clean_text(topic.get("page_type", "")).lower()

    tokens: List[str] = []
    for pattern, mapped in RULE_TOKENS.items():
        if pattern in haystack:
            tokens.extend(mapped)

    words = re.findall(r"[a-z0-9]+", haystack)
    for word in words:
        if len(word) < 4 or word in STOPWORDS:
            continue
        tokens.append(_normalize_word(word))

    return _dedupe_preserve(tokens)


def _topic_phrase_candidates(topic: Dict[str, str]) -> List[str]:
    seed_text = _clean_text(topic.get("primary_keyword", "")) or _clean_text(topic.get("title", ""))
    words = [
        _normalize_word(word)
        for word in re.findall(r"[a-z0-9]+", seed_text.lower())
        if len(word) >= 4 and word not in STOPWORDS
    ]

    phrases: List[str] = []
    for index in range(len(words) - 1):
        phrase = f"{words[index]} {words[index + 1]}".strip()
        if phrase and phrase not in phrases:
            phrases.append(phrase)
    return phrases


def _strong_tokens(tokens: List[str]) -> List[str]:
    return [token for token in tokens if token not in WEAK_TOKENS]


def _score_product(product: Dict[str, Any], tokens: List[str]) -> Tuple[int, List[str], List[str]]:
    score = 0
    matched: List[str] = []
    matched_name_tokens: List[str] = []
    category_text = product.get("_category_text", "")
    name_text = product.get("_name_text", "")
    description_text = product.get("_description_text", "")

    for token in tokens:
        if token and token in name_text:
            score += 5
            matched.append(token)
            matched_name_tokens.append(token)
            continue
        if token and token in category_text:
            score += 3
            matched.append(token)
            continue
        if token and token in description_text:
            score += 1
            matched.append(token)

    return score, matched, matched_name_tokens


def _matched_phrases(product: Dict[str, Any], phrases: List[str]) -> List[str]:
    normalized_name = product.get("_normalized_name_text", "")
    return [phrase for phrase in phrases if phrase and phrase in normalized_name]


def _matched_fallback_phrases(product: Dict[str, Any], phrases: List[str]) -> List[Tuple[str, str]]:
    normalized_name = product.get("_normalized_name_text", "")
    normalized_category = product.get("_normalized_category_text", "")
    normalized_description = product.get("_normalized_description_text", "")
    matched: List[Tuple[str, str]] = []
    for phrase in phrases:
        if not phrase:
            continue
        normalized_phrase = _normalize_phrase_text(phrase)
        if not normalized_phrase:
            continue
        if normalized_phrase in normalized_name:
            matched.append((phrase, "name"))
        elif normalized_phrase in normalized_category:
            matched.append((phrase, "category"))
        elif normalized_phrase in normalized_description:
            matched.append((phrase, "description"))
    return matched


def _topic_wants_large_pack(topic: Dict[str, str]) -> bool:
    seed_text = _topic_seed_text(topic).lower()
    compact = re.sub(r"\s+", "", seed_text)
    return bool(re.search(r"\d+(?:[.,]\d+)?kg", compact)) or any(
        token in seed_text for token in ["bulk", "wholesale", "box", "boxes", "large pack"]
    )


def _topic_prefers_small_pack(topic: Dict[str, str]) -> bool:
    seed_text = _topic_seed_text(topic).lower()
    page_type = _clean_text(topic.get("page_type", "")).lower()
    if page_type != "guide_page":
        return False
    return any(token in seed_text for token in ["halal", "vegan", "kosher", "gelatine", "gelatin", "ingredient", "ingredients", "gluten", "allergen"])


def _product_pack_flags(product: Dict[str, Any]) -> Tuple[bool, bool]:
    category = _clean_text(product.get("category", "")).lower()
    name = _clean_text(product.get("product_name", "")).lower()
    compact_name = re.sub(r"\s+", "", name)
    is_wholesale = "wholesale" in category
    is_large_pack = bool(re.search(r"\d+(?:[.,]\d+)?kg", compact_name)) or any(token in name for token in ["bulk", "box", "boxes"])
    return is_wholesale, is_large_pack


def _explicit_substitute_phrases(topic: Dict[str, str]) -> List[str]:
    hints = _load_substitute_hints()
    lowered = _clean_text(_topic_seed_text(topic)).lower()
    normalized = _normalize_phrase_text(_topic_seed_text(topic))
    for trigger, phrases in hints.items():
        if trigger in lowered or trigger in normalized:
            return phrases
    return []


def _generic_family_phrases(topic: Dict[str, str]) -> List[str]:
    seed_text = _topic_seed_text(topic).lower()
    normalized = _normalize_phrase_text(seed_text)
    category = _clean_text(topic.get("category_hint", "")).lower()

    phrases: List[str] = []
    for trigger, mapped in FAMILY_FALLBACK_PHRASES.items():
        if trigger in seed_text or trigger in normalized:
            phrases.extend(mapped)
    for trigger, mapped in CATEGORY_FALLBACK_PHRASES.items():
        if trigger in category:
            phrases.extend(mapped)

    if not phrases:
        phrases.extend(
            token
            for token in _topic_tokens(topic)
            if token not in WEAK_TOKENS and token not in STOPWORDS
        )

    return _dedupe_preserve(phrases, limit=8)


def _build_fallback_profile(topic: Dict[str, str]) -> Tuple[List[str], str]:
    explicit = _explicit_substitute_phrases(topic)
    if explicit:
        return explicit, "substitute_hint"

    generic = _generic_family_phrases(topic)
    if generic:
        return generic, "generic_family"

    return [], ""


def _select_fallback_products(
    topic: Dict[str, str],
    product_catalog: List[Dict[str, Any]],
    max_items: int = 4,
) -> List[Dict[str, Any]]:
    phrases, reason = _build_fallback_profile(topic)
    if not phrases:
        return []

    wants_large_pack = _topic_wants_large_pack(topic)
    scored_rows: List[Tuple[int, bool, str, Dict[str, Any]]] = []
    for product in product_catalog:
        matched = _matched_fallback_phrases(product, phrases)
        if not matched:
            continue

        category = _clean_text(product.get("category", "")).lower()
        name = _clean_text(product.get("product_name", "")).lower()
        compact_name = re.sub(r"\s+", "", name)
        is_non_wholesale = "wholesale" not in category

        score = 0
        matched_phrases: List[str] = []
        for phrase, source in matched:
            matched_phrases.append(phrase)
            if source == "name":
                score += 12 if phrase == phrases[0] else 8
            elif source == "category":
                score += 6 if phrase == phrases[0] else 4
            else:
                score += 3 if phrase == phrases[0] else 2

        if is_non_wholesale:
            score += 4
        if "old fashion" in category or "chocolate" in category:
            score += 2
        if wants_large_pack and re.search(r"\d+(?:[.,]\d+)?kg", compact_name):
            score += 5
        if wants_large_pack and not is_non_wholesale:
            score += 2

        item = {
            "product_name": product.get("product_name", ""),
            "category": product.get("category", ""),
            "description": product.get("description", ""),
            "price": product.get("price", ""),
            "url": product.get("url", ""),
            "image_url": product.get("image_url", ""),
            "matched_tokens": [reason],
            "matched_phrases": _dedupe_preserve(matched_phrases),
            "selection_reason": "fallback_large_pack" if wants_large_pack else reason,
        }
        scored_rows.append((score, is_non_wholesale, item["product_name"].lower(), item))

    scored_rows.sort(key=lambda row: (-row[0], not row[1], row[2]))
    if not wants_large_pack and any(row[1] for row in scored_rows):
        scored_rows = [row for row in scored_rows if row[1]]

    selected: List[Dict[str, Any]] = []
    seen_names = set()
    for _, _, _, item in scored_rows:
        key = item["product_name"].lower()
        if key in seen_names:
            continue
        seen_names.add(key)
        selected.append(item)
        if len(selected) >= max_items:
            break

    return selected


def select_products_for_topic(topic: Dict[str, str], product_catalog: List[Dict[str, Any]], max_items: int = 4) -> List[Dict[str, Any]]:
    if not product_catalog:
        return []

    tokens = _topic_tokens(topic)
    if not tokens:
        return []

    strong_tokens = _strong_tokens(tokens)
    phrase_candidates = _topic_phrase_candidates(topic)
    prefer_small_pack = _topic_prefers_small_pack(topic)

    scored_rows: List[Tuple[int, bool, bool, bool, str, Dict[str, Any]]] = []
    has_phrase_hits = False

    for product in product_catalog:
        score, matched, matched_name_tokens = _score_product(product, tokens)
        if score <= 0:
            continue

        matched_phrases = _matched_phrases(product, phrase_candidates)
        if matched_phrases:
            has_phrase_hits = True
            score += 8 * len(matched_phrases)

        if strong_tokens and not any(token in matched_name_tokens for token in strong_tokens):
            if not matched_phrases:
                continue

        is_wholesale, is_large_pack = _product_pack_flags(product)
        if prefer_small_pack:
            if is_wholesale:
                score -= 6
            if is_large_pack:
                score -= 4
            if not is_wholesale and not is_large_pack:
                score += 3

        item = {
            "product_name": product.get("product_name", ""),
            "category": product.get("category", ""),
            "description": product.get("description", ""),
            "price": product.get("price", ""),
            "url": product.get("url", ""),
            "image_url": product.get("image_url", ""),
            "matched_tokens": matched,
            "matched_phrases": matched_phrases,
            "selection_reason": "direct_match",
        }
        scored_rows.append((score, bool(matched_phrases), is_wholesale, is_large_pack, item["product_name"].lower(), item))

    if has_phrase_hits:
        scored_rows = [row for row in scored_rows if row[1]]

    scored_rows.sort(key=lambda row: (-row[0], row[2], row[3], row[4]))

    selected: List[Dict[str, Any]] = []
    seen_names = set()
    for _, _, _, _, _, item in scored_rows:
        key = item["product_name"].lower()
        if key in seen_names:
            continue
        seen_names.add(key)
        selected.append(item)
        if len(selected) >= max_items:
            break

    if selected:
        return selected

    return _select_fallback_products(topic, product_catalog, max_items=max_items)


# Session-level URL validation cache so each URL is only checked once per run.
_url_validation_cache: Dict[str, bool] = {}


def _is_homepage(url: str) -> bool:
    """Return True if the URL resolves to the site root (homepage redirect = product not found)."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return path == "" or path == "/index.php"


def validate_product_urls(
    products: List[Dict[str, Any]],
    timeout: int = 5,
) -> List[Dict[str, Any]]:
    """Filter out products whose URL does not return a live product page.

    WooCommerce redirects deleted/unavailable products to the homepage (301 → /),
    so we must reject URLs whose final destination is the homepage even if the
    HTTP status is 200.

    Results are cached per URL for the lifetime of the process.
    """
    valid = []
    for product in products:
        url = product.get("url") or product.get("product_url") or ""
        if not url:
            valid.append(product)
            continue

        if url not in _url_validation_cache:
            try:
                resp = requests.head(url, allow_redirects=True, timeout=timeout)
                final_url = resp.url  # URL after all redirects
                if resp.status_code >= 400:
                    ok = False
                    logger.warning(f"Product URL returned {resp.status_code}, excluded: {url}")
                elif _is_homepage(final_url):
                    ok = False
                    logger.warning(
                        f"Product URL redirects to homepage (product likely deleted), excluded: {url} → {final_url}"
                    )
                else:
                    ok = True
            except Exception as exc:
                logger.warning(f"Product URL check failed ({url}): {exc} — keeping product (fail-open)")
                ok = True
            _url_validation_cache[url] = ok

        if _url_validation_cache[url]:
            valid.append(product)
        else:
            logger.warning(f"Excluded invalid product URL from content: {url}")

    return valid


def pick_featured_image_url(selected_products: List[Dict[str, Any]]) -> str:
    """Return the first usable site image URL from the selected products."""
    for product in selected_products:
        image_url = _clean_text(product.get("image_url", ""))
        if image_url:
            return image_url
    return ""
