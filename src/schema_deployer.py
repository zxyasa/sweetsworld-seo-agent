"""Deploy LocalBusiness JSON-LD schema to WordPress via Code Snippets API.

Reads `local_business` config from site.json and creates/updates a persistent
PHP snippet that injects the schema into <head> on specified pages.

Usage:
    python -m schema_deployer --site sweetsworld
    python -m schema_deployer --site newcastlehub
    python -m schema_deployer --site sweetsworld --remove
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SNIPPET_NAME_PREFIX = "LocalBusiness Schema"
SITES_DIR = Path(__file__).resolve().parent.parent / "sites"


def load_site_config(site_id: str) -> dict[str, Any]:
    site_json = SITES_DIR / site_id / "site.json"
    if not site_json.exists():
        raise FileNotFoundError(f"site.json not found: {site_json}")
    return json.loads(site_json.read_text())


def load_site_env(site_id: str) -> dict[str, str]:
    """Load .env from site directory into os.environ. Returns the loaded vars."""
    env_file = SITES_DIR / site_id / ".env"
    loaded: dict[str, str] = {}
    if not env_file.exists():
        return loaded
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        k, v = key.strip(), value.strip()
        os.environ[k] = v
        loaded[k] = v
    return loaded


def build_jsonld(config: dict[str, Any], base_url: str) -> dict[str, Any]:
    """Build a schema.org LocalBusiness JSON-LD dict from site config."""
    lb = config["local_business"]

    schema: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": lb["type"],
        "name": lb["name"],
        "url": base_url.rstrip("/"),
        "telephone": lb["telephone"],
    }

    if lb.get("logo"):
        schema["logo"] = lb["logo"]
        schema["image"] = lb["logo"]

    addr = lb.get("address")
    if addr:
        postal = {"@type": "PostalAddress"}
        for field in ("streetAddress", "addressLocality", "addressRegion",
                      "postalCode", "addressCountry"):
            if addr.get(field):
                postal[field] = addr[field]
        schema["address"] = postal

    geo = lb.get("geo")
    if geo and geo.get("latitude") is not None:
        schema["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": geo["latitude"],
            "longitude": geo["longitude"],
        }

    hours = lb.get("openingHours", [])
    if hours:
        schema["openingHoursSpecification"] = [
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": h["days"],
                "opens": h["opens"],
                "closes": h["closes"],
            }
            for h in hours
        ]

    if lb.get("priceRange"):
        schema["priceRange"] = lb["priceRange"]

    same_as = lb.get("sameAs", [])
    if same_as:
        schema["sameAs"] = same_as

    return schema


def build_php_snippet(jsonld: dict[str, Any], inject_on: list[str]) -> str:
    """Wrap JSON-LD in a PHP snippet that only fires on specified pages."""
    conditions = []
    for page in inject_on:
        if page == "front_page":
            conditions.append("is_front_page()")
        else:
            conditions.append(f'is_page("{page}")')

    condition_str = " || ".join(conditions) if conditions else "true"
    json_str = json.dumps(jsonld, indent=2, ensure_ascii=False)

    return (
        f'add_action("wp_head", function() {{\n'
        f"    if (!({condition_str})) return;\n"
        f"    echo '<script type=\"application/ld+json\">\n"
        f"{json_str}\n"
        f"</script>';\n"
        f"}}, 1);\n"
    )


class SnippetClient:
    """Thin wrapper around the WP Code Snippets REST API."""

    def __init__(self, base_url: str, username: str, app_password: str):
        self.api_url = f"{base_url.rstrip('/')}/wp-json/code-snippets/v1/snippets"
        creds = f"{username}:{app_password}"
        self.auth = "Basic " + base64.b64encode(creds.encode()).decode()

    def _request(self, url: str, method: str = "GET",
                 data: dict | None = None) -> Any:
        body = json.dumps(data, ensure_ascii=False).encode() if data else None
        req = urllib.request.Request(
            url, data=body, method=method,
            headers={
                "Authorization": self.auth,
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())

    def find_by_name(self, name_prefix: str) -> dict | None:
        """Find an existing snippet whose name starts with prefix."""
        snippets = self._request(self.api_url)
        for s in snippets:
            if s.get("name", "").startswith(name_prefix):
                return s
        return None

    def create(self, name: str, code: str) -> dict:
        return self._request(self.api_url, "POST", {
            "name": name,
            "code": code,
            "active": True,
            "scope": "global",
            "priority": 10,
        })

    def delete(self, snippet_id: int) -> None:
        self._request(f"{self.api_url}/{snippet_id}", "DELETE")

    def deploy(self, name: str, code: str) -> dict:
        """Idempotent deploy: delete old snippet if exists, then create new."""
        existing = self.find_by_name(name)
        if existing:
            old_id = existing["id"]
            logger.info("Found existing snippet id=%s, replacing...", old_id)
            self.delete(old_id)
        result = self.create(name, code)
        logger.info("Deployed snippet id=%s, active=%s", result["id"], result["active"])
        return result

    def remove(self, name: str) -> bool:
        """Remove snippet by name prefix. Returns True if found and removed."""
        existing = self.find_by_name(name)
        if existing:
            self.delete(existing["id"])
            logger.info("Removed snippet id=%s", existing["id"])
            return True
        logger.info("No snippet found with name prefix '%s'", name)
        return False


def deploy_local_business_schema(site_id: str, dry_run: bool = False) -> dict:
    """Main entry: read config, build schema, deploy to WP."""
    config = load_site_config(site_id)
    lb = config.get("local_business")
    if not lb:
        raise ValueError(f"No 'local_business' section in {site_id}/site.json")

    load_site_env(site_id)

    base_url = config["base_url"]
    jsonld = build_jsonld(config, base_url)
    inject_on = lb.get("inject_on", ["front_page", "contact"])
    php_code = build_php_snippet(jsonld, inject_on)
    snippet_name = f"{SNIPPET_NAME_PREFIX} ({config['display_name']})"

    if dry_run:
        print(f"--- Dry run for {site_id} ---")
        print(f"Snippet name: {snippet_name}")
        print(f"Inject on: {inject_on}")
        print(f"\nJSON-LD:\n{json.dumps(jsonld, indent=2, ensure_ascii=False)}")
        print(f"\nPHP:\n{php_code}")
        return {"dry_run": True, "jsonld": jsonld}

    wp_conf = config.get("wp", {})
    username = os.environ.get(wp_conf.get("env_username", "WP_USERNAME"), "")
    password = os.environ.get(wp_conf.get("env_password", "WP_APP_PASSWORD"), "")
    if not username or not password:
        raise RuntimeError("WP credentials not found in env")

    client = SnippetClient(base_url, username, password)
    result = client.deploy(snippet_name, php_code)
    print(f"Deployed: snippet id={result['id']} on {base_url}")
    return result


def remove_local_business_schema(site_id: str) -> bool:
    config = load_site_config(site_id)
    load_site_env(site_id)
    base_url = config["base_url"]
    snippet_name = f"{SNIPPET_NAME_PREFIX} ({config['display_name']})"

    wp_conf = config.get("wp", {})
    username = os.environ.get(wp_conf.get("env_username", "WP_USERNAME"), "")
    password = os.environ.get(wp_conf.get("env_password", "WP_APP_PASSWORD"), "")

    client = SnippetClient(base_url, username, password)
    return client.remove(snippet_name)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Deploy LocalBusiness schema to WordPress")
    parser.add_argument("--site", required=True, help="Site ID (directory name under sites/)")
    parser.add_argument("--dry-run", action="store_true", help="Print schema without deploying")
    parser.add_argument("--remove", action="store_true", help="Remove existing schema snippet")
    args = parser.parse_args()

    if args.remove:
        remove_local_business_schema(args.site)
    else:
        deploy_local_business_schema(args.site, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
