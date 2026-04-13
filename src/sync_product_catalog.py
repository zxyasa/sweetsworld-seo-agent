"""
Sync WooCommerce product catalog → data/products.json

使用 wc/v3 认证 API，拉取全部已发布产品（含缺货）。
URL 可访问性由 product_url_health_check.py 负责验证，这里不过滤库存状态。
"""
from __future__ import annotations

import argparse
import html
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE_URL = "https://sweetsworld.com.au"


def _load_credentials() -> tuple[str, str]:
    """从 .env 读取 WP 认证信息。"""
    env_path = PROJECT_ROOT / ".env"
    username, password = "", ""
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("WP_USERNAME="):
                username = line.split("=", 1)[1].strip()
            elif line.startswith("WP_APP_PASSWORD="):
                password = line.split("=", 1)[1].strip()
    username = username or os.getenv("WP_USERNAME", "")
    password = password or os.getenv("WP_APP_PASSWORD", "")
    return username, password


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _html_to_text(value: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", value or "", flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return _clean_text(html.unescape(text))


def fetch_all_products(base_url: str, username: str, password: str, per_page: int = 100) -> List[Dict[str, Any]]:
    """通过 wc/v3 API 拉取全部已发布产品（分页，自动翻页）。"""
    auth = HTTPBasicAuth(username, password)
    endpoint = f"{base_url.rstrip('/')}/wp-json/wc/v3/products"
    all_products: List[Dict[str, Any]] = []
    page = 1

    while True:
        params = {
            "status": "any",   # publish / draft / private / pending / trash
            "per_page": per_page,
            "page": page,
            "orderby": "id",
            "order": "asc",
        }
        resp = requests.get(endpoint, params=params, auth=auth, timeout=30)
        resp.raise_for_status()
        chunk = resp.json()

        if not chunk:
            break

        all_products.extend(chunk)
        total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
        total_count = int(resp.headers.get("X-WP-Total", len(all_products)))

        logger.info(f"  页 {page}/{total_pages}：已拉取 {len(all_products)}/{total_count} 个产品")

        if page >= total_pages:
            break
        page += 1

    return all_products


def normalize_product(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """标准化单个产品记录。"""
    if not isinstance(row, dict):
        return None

    name = _clean_text(row.get("name", ""))
    url = _clean_text(row.get("permalink", ""))
    if not name or not url:
        return None

    # 分类
    categories = row.get("categories", []) or []
    category_names = [_clean_text(c.get("name", "")) for c in categories if isinstance(c, dict)]
    category_names = [c for c in category_names if c]
    category = category_names[0] if category_names else ""

    # 标签
    tags = row.get("tags", []) or []
    tag_names = [_clean_text(t.get("name", "")) for t in tags if isinstance(t, dict)]
    tag_names = [t for t in tag_names if t]

    # 图片
    images = row.get("images", []) or []
    image_url = ""
    for img in images:
        if isinstance(img, dict) and img.get("src"):
            image_url = _clean_text(img["src"])
            break

    # 描述（截断到 220 字符）
    description = _html_to_text(row.get("short_description") or row.get("description") or "")
    if len(description) > 220:
        description = description[:217].rsplit(" ", 1)[0].rstrip(",.;:-") + "..."

    # 价格
    price = _clean_text(row.get("price", "") or row.get("regular_price", ""))

    # 库存状态
    stock_status = _clean_text(row.get("stock_status", ""))  # instock / outofstock / onbackorder
    is_in_stock = stock_status == "instock"

    return {
        "product_name": name,
        "category": category,
        "description": description,
        "price": price,
        "url": url,
        "slug": _clean_text(row.get("slug", "")),
        "sku": _clean_text(row.get("sku", "")),
        "tags": tag_names,
        "categories": category_names,
        "image_url": image_url,
        "is_in_stock": is_in_stock,
        "stock_status": stock_status,
        "wp_status": _clean_text(row.get("status", "")),  # publish / draft / private / pending
        "source": "wc_v3_api",
        "source_id": row.get("id"),
    }


def write_catalog(path: Path, products: List[Dict[str, Any]], base_url: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "wc_v3_api",
        "base_url": base_url,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(products),
        "products": products,
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync all WooCommerce products → data/products.json")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output", default="data/products.json")
    parser.add_argument("--per-page", type=int, default=100)
    args = parser.parse_args()

    username, password = _load_credentials()
    if not username or not password:
        logger.error("ERROR: WP_USERNAME / WP_APP_PASSWORD 未配置")
        return 1

    output_path = PROJECT_ROOT / args.output
    logger.info(f"开始同步产品目录：{args.base_url}")
    logger.info(f"认证用户：{username}")

    raw_rows = fetch_all_products(args.base_url, username, password, per_page=args.per_page)
    logger.info(f"\n共拉取 {len(raw_rows)} 条原始记录，开始标准化...")

    products, seen = [], set()
    for row in raw_rows:
        normalized = normalize_product(row)
        if not normalized:
            continue
        key = normalized["url"].lower()
        if key in seen:
            continue
        seen.add(key)
        products.append(normalized)

    from collections import Counter
    status_counts = Counter(p["wp_status"] for p in products)
    in_stock = sum(1 for p in products if p["is_in_stock"])
    out_of_stock = len(products) - in_stock

    write_catalog(output_path, products, args.base_url)

    logger.info(f"\n✅ 同步完成")
    logger.info(f"   总产品数：{len(products)}")
    logger.info(f"   按状态分布：")
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        logger.info(f"     {status:12}: {count}")
    logger.info(f"   有库存：  {in_stock}")
    logger.info(f"   缺货：    {out_of_stock}")
    logger.info(f"   输出：    {output_path}")

    print(json.dumps({"output": str(output_path), "count": len(products),
                      "by_status": dict(status_counts),
                      "in_stock": in_stock, "out_of_stock": out_of_stock}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
