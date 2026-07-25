"""Provider adapters and evidence extraction for read-only AIO probes.

Provider labels name the API surface that was actually measured. Responses
web search is not labelled as ChatGPT, and Gemini grounding is not labelled as
Google AI Overviews.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import requests


@dataclass(frozen=True)
class ProbeResult:
    provider: str
    surface: str
    model: str
    model_version: str = ""
    answer_text: str = ""
    citation_urls: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


class ProbeAPIError(RuntimeError):
    def __init__(self, provider: str, status_code: int, message: str, raw: Any = None) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.raw = raw


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def parse_openai_response(payload: dict[str, Any], latency_ms: int | None = None) -> ProbeResult:
    text_parts: list[str] = []
    citations: list[str] = []
    sources: list[str] = []
    for item in payload.get("output", []):
        if item.get("type") == "web_search_call":
            for source in (item.get("action") or {}).get("sources", []):
                if isinstance(source, dict):
                    sources.append(str(source.get("url") or ""))
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") != "output_text":
                continue
            text_parts.append(str(part.get("text") or ""))
            for annotation in part.get("annotations", []):
                if annotation.get("type") == "url_citation":
                    citations.append(str(annotation.get("url") or ""))
    usage = payload.get("usage") or {}
    model = str(payload.get("model") or "")
    return ProbeResult(
        provider="openai",
        surface="responses_web_search_api",
        model=model,
        model_version=model,
        answer_text="\n".join(part for part in text_parts if part).strip(),
        citation_urls=_unique(citations),
        source_urls=_unique(sources + citations),
        latency_ms=latency_ms,
        input_tokens=usage.get("input_tokens"),
        output_tokens=usage.get("output_tokens"),
        raw_response=payload,
    )


def query_openai(
    query: str,
    api_key: str,
    model: str,
    location: dict[str, Any],
    timeout: int = 90,
    session: requests.Session | None = None,
) -> ProbeResult:
    client = session or requests.Session()
    body = {
        "model": model,
        "input": query,
        "tools": [{"type": "web_search", "user_location": {"type": "approximate", **location}}],
        "include": ["web_search_call.action.sources"],
    }
    started = time.monotonic()
    response = client.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=body,
        timeout=timeout,
    )
    latency_ms = round((time.monotonic() - started) * 1000)
    try:
        payload = response.json()
    except ValueError:
        payload = {"error": {"message": response.text[:1000]}}
    if response.status_code >= 400:
        message = str((payload.get("error") or {}).get("message") or f"HTTP {response.status_code}")
        raise ProbeAPIError("openai", response.status_code, message, payload)
    return parse_openai_response(payload, latency_ms)


def parse_gemini_response(
    payload: dict[str, Any], requested_model: str, latency_ms: int | None = None
) -> ProbeResult:
    candidates = payload.get("candidates") or []
    candidate = candidates[0] if candidates else {}
    parts = ((candidate.get("content") or {}).get("parts") or [])
    answer = "\n".join(str(part.get("text") or "") for part in parts if isinstance(part, dict)).strip()
    metadata = candidate.get("groundingMetadata") or {}
    urls: list[str] = []
    titled_sources: list[str] = []
    for chunk in metadata.get("groundingChunks") or []:
        web = (chunk or {}).get("web") or {}
        urls.append(str(web.get("uri") or ""))
        title = str(web.get("title") or "").strip().casefold()
        # Gemini frequently returns an opaque Google redirect URI while the
        # source title is the actual hostname. Preserve the redirect as the
        # citation and add a normalised hostname URL for domain attribution.
        if re.fullmatch(r"(?:www\.)?[a-z0-9][a-z0-9.-]*\.[a-z]{2,}", title):
            titled_sources.append(f"https://{title.removeprefix('www.')}/")
    usage = payload.get("usageMetadata") or {}
    model_version = str(payload.get("modelVersion") or requested_model)
    return ProbeResult(
        provider="google",
        surface="gemini_grounding_api",
        model=requested_model,
        model_version=model_version,
        answer_text=answer,
        citation_urls=_unique(urls),
        source_urls=_unique(urls + titled_sources),
        latency_ms=latency_ms,
        input_tokens=usage.get("promptTokenCount"),
        output_tokens=usage.get("candidatesTokenCount"),
        raw_response=payload,
    )


def query_gemini(
    query: str,
    api_key: str,
    model: str,
    location: dict[str, Any],
    timeout: int = 90,
    session: requests.Session | None = None,
) -> ProbeResult:
    client = session or requests.Session()
    location_hint = ", ".join(
        str(location[key]) for key in ("city", "region", "country") if location.get(key)
    )
    prompt = query + (f"\n\nUse the perspective of a shopper located in {location_hint}." if location_hint else "")
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
    }
    started = time.monotonic()
    response = client.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json=body,
        timeout=timeout,
    )
    latency_ms = round((time.monotonic() - started) * 1000)
    try:
        payload = response.json()
    except ValueError:
        payload = {"error": {"message": response.text[:1000]}}
    if response.status_code >= 400:
        message = str((payload.get("error") or {}).get("message") or f"HTTP {response.status_code}")
        raise ProbeAPIError("google", response.status_code, message, payload)
    return parse_gemini_response(payload, model, latency_ms)


def analyse_evidence(
    answer_text: str,
    citation_urls: list[str],
    source_urls: list[str],
    brand_aliases: list[str],
    domain: str,
    competitors: list[dict[str, Any]],
) -> dict[str, Any]:
    """Extract deterministic metrics; recommendation is a conservative heuristic."""
    lowered = answer_text.casefold()
    aliases = [alias.casefold() for alias in brand_aliases]
    brand_positions = [lowered.find(alias) for alias in aliases if lowered.find(alias) >= 0]
    brand_mentioned = bool(brand_positions)
    all_urls = _unique(citation_urls + source_urls)

    def is_own_url(value: str) -> bool:
        host = (urlparse(value).hostname or "").casefold()
        target = domain.casefold()
        return host == target or host.endswith("." + target)

    own_urls = [url for url in all_urls if is_own_url(url)]
    domain_cited = bool(own_urls)
    product_cited = any("/candy/" in urlparse(url).path.casefold() for url in own_urls)
    recommendation_terms = re.compile(
        r"\b(recommend(?:ed|s|ation)?|best|top|try|choice|option|shop|store|buy|order|stock(?:s|ed)?|available)\b",
        re.IGNORECASE,
    )
    brand_recommended = False
    if brand_mentioned:
        brand_recommended = any(
            recommendation_terms.search(answer_text[max(0, position - 140): position + 240])
            for position in brand_positions
        )

    ranked: list[tuple[int, str]] = []
    if brand_positions:
        ranked.append((min(brand_positions), "Sweetsworld"))
    mentioned_competitors: list[str] = []
    for competitor in competitors:
        names = [str(competitor.get("name") or "")] + [str(x) for x in competitor.get("aliases", [])]
        positions = [lowered.find(name.casefold()) for name in names if name and lowered.find(name.casefold()) >= 0]
        if positions:
            name = str(competitor.get("name") or names[0])
            mentioned_competitors.append(name)
            ranked.append((min(positions), name))
    ranked.sort(key=lambda pair: pair[0])
    recommendation_position = None
    if brand_recommended:
        recommendation_position = next(
            (index for index, (_, name) in enumerate(ranked, 1) if name == "Sweetsworld"), None
        )
    return {
        "brand_mentioned": brand_mentioned,
        "brand_recommended": brand_recommended,
        "domain_cited": domain_cited,
        "product_cited": product_cited,
        "recommendation_position": recommendation_position,
        "competitors": mentioned_competitors,
    }
