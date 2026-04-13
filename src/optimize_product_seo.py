"""
批量优化 WooCommerce 产品的 RankMath SEO meta。

规则：
- 已有值的字段 → 保留不动
- 缺失的字段 → 自动生成并填入
- 只处理 wp_status=publish 的产品
"""
from __future__ import annotations

import argparse
import html
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_JSON = PROJECT_ROOT / "data" / "products.json"

_WP_PRODUCT_ENDPOINT = "wp-json/wp/v2/product"


def _clean(text: Any) -> str:
    t = re.sub(r"<[^>]+>", " ", str(text or ""))
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def _build_keyword(name: str) -> str:
    """生成 focus keyword：产品名小写。"""
    return _clean(name).lower()


def _build_seo_title(name: str, brand: str = "SweetsWorld") -> str:
    """SEO title：产品名 + 品牌尾缀。"""
    clean_name = _clean(name)
    return f"{clean_name} | Buy Online Australia | {brand}"


def _build_meta_description(name: str, description: str, categories: List[str], brand: str = "SweetsWorld") -> str:
    """Meta description：优先用产品描述前 150 字符，否则用模板。"""
    desc = _clean(description)
    if len(desc) >= 50:
        return desc[:157].rstrip() + "..." if len(desc) > 160 else desc

    cat = categories[0] if categories else "Confectionery"
    return (
        f"Buy {_clean(name)} online in Australia. "
        f"{cat} available at {brand} with fast delivery Australia-wide."
    )


def _load_products_map() -> Dict[int, Dict]:
    """从 products.json 建 source_id → product 映射。"""
    data = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
    products = data.get("products", [])
    return {int(p["source_id"]): p for p in products if p.get("source_id")}


def _fetch_all_products(base_url: str, auth: Tuple[str, str]) -> List[Dict]:
    """通过 WP REST API 拉取全部已发布产品（含 meta）。"""
    url = f"{base_url}/{_WP_PRODUCT_ENDPOINT}"
    all_products: List[Dict] = []
    page = 1
    while True:
        resp = requests.get(
            url,
            params={"status": "publish", "per_page": 100, "page": page, "context": "edit",
                    "_fields": "id,slug,title,meta"},
            auth=auth,
            timeout=30,
        )
        if resp.status_code == 404:
            logger.error("ERROR: WP REST API product endpoint not found. Check post type REST base.")
            break
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        all_products.extend(batch)
        total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
        logger.info(f"  页 {page}/{total_pages}：已拉取 {len(all_products)} 个产品")
        if page >= total_pages:
            break
        page += 1
    return all_products


def _needs_update(meta: Dict) -> Tuple[bool, List[str]]:
    """返回 (需要更新, 缺失字段列表)。"""
    missing = []
    for field in ["rank_math_focus_keyword", "rank_math_title", "rank_math_description"]:
        if not str(meta.get(field) or "").strip():
            missing.append(field)
    return bool(missing), missing


def optimize_products(
    base_url: str,
    auth: Tuple[str, str],
    dry_run: bool = False,
    limit: Optional[int] = None,
    brand: str = "SweetsWorld",
) -> Dict[str, int]:
    products_map = _load_products_map()
    logger.info(f"products.json 中产品数：{len(products_map)}")

    logger.info("拉取 WP 产品列表...")
    wp_products = _fetch_all_products(base_url, auth)
    logger.info(f"WP 已发布产品：{len(wp_products)} 个")

    stats = {"total": len(wp_products), "updated": 0, "skipped": 0, "errors": 0}

    targets = [p for p in wp_products if _needs_update(p.get("meta", {}))[0]]
    logger.info(f"需要补充 SEO meta：{len(targets)} 个（已完整：{len(wp_products) - len(targets)} 个）")

    if limit:
        targets = targets[:limit]
        logger.info(f"（限制处理前 {limit} 个）")

    for i, product in enumerate(targets, 1):
        post_id = product["id"]
        slug = product.get("slug", "")
        raw_title = product.get("title", {})
        title_text = _clean(raw_title.get("rendered", "") if isinstance(raw_title, dict) else raw_title)
        meta = product.get("meta", {})

        # 从 products.json 取详细信息
        catalog_entry = products_map.get(post_id, {})
        description = catalog_entry.get("description", "")
        categories = catalog_entry.get("categories", [])
        product_name = catalog_entry.get("product_name", "") or title_text

        _, missing_fields = _needs_update(meta)

        payload_meta: Dict[str, str] = {}
        if "rank_math_focus_keyword" in missing_fields:
            payload_meta["rank_math_focus_keyword"] = _build_keyword(product_name)
        if "rank_math_title" in missing_fields:
            payload_meta["rank_math_title"] = _build_seo_title(product_name, brand=brand)
        if "rank_math_description" in missing_fields:
            payload_meta["rank_math_description"] = _build_meta_description(
                product_name, description, categories, brand=brand
            )

        logger.info(f"[{i}/{len(targets)}] {slug} — 补充: {', '.join(missing_fields)}")

        if dry_run:
            for k, v in payload_meta.items():
                logger.info(f"    {k}: {v[:80]}")
            stats["skipped"] += 1
            continue

        try:
            resp = requests.post(
                f"{base_url}/{_WP_PRODUCT_ENDPOINT}/{post_id}",
                json={"meta": payload_meta},
                auth=auth,
                timeout=15,
            )
            if resp.status_code == 200:
                stats["updated"] += 1
            else:
                logger.warning(f"  ✗ HTTP {resp.status_code}: {resp.text[:100]}")
                stats["errors"] += 1
        except Exception as exc:
            logger.error(f"  ✗ 请求失败: {exc}")
            stats["errors"] += 1

        time.sleep(0.3)

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="批量优化 WooCommerce 产品 RankMath SEO meta")
    parser.add_argument("--dry-run", action="store_true", help="只显示计划，不实际写入")
    parser.add_argument("--limit", type=int, help="限制处理产品数量（测试用）")
    parser.add_argument("--brand", default=None, help="品牌名（默认从 WP_BASE_URL 或 SITE_BRAND 环境变量读取）")
    args = parser.parse_args()

    base_url = os.environ.get("WP_BASE_URL", "").rstrip("/")
    username = os.environ.get("WP_USERNAME", "")
    password = os.environ.get("WP_APP_PASSWORD", "")
    brand = args.brand or os.environ.get("SITE_BRAND", "SweetsWorld")

    if not all([base_url, username, password]):
        logger.error("ERROR: 请在 .env 中配置 WP_BASE_URL / WP_USERNAME / WP_APP_PASSWORD")
        raise SystemExit(1)

    auth = (username, password)
    mode = "DRY RUN" if args.dry_run else "LIVE"
    logger.info(f"=== 产品 SEO 优化 [{mode}] ===")

    stats = optimize_products(base_url, auth, dry_run=args.dry_run, limit=args.limit, brand=brand)

    logger.info("=" * 50)
    logger.info(f"总产品数：{stats['total']}")
    logger.info(f"已更新：  {stats['updated']}")
    logger.info(f"跳过：    {stats['skipped']}")
    logger.info(f"错误：    {stats['errors']}")


if __name__ == "__main__":
    main()
