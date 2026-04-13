"""
产品健康检查：对比 Lightspeed（库存真相）与 WooCommerce（展示层）
找出：
  1. 应发布但在草稿的产品（LS active + WC draft）
  2. 已停产但仍在售的产品（LS deleted + WC publish）
  3. WC 有但 LS 完全没有 SKU 的产品（孤儿产品）
  4. URL 死链（已有逻辑，此处整合）
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Any

# ── 配置 ────────────────────────────────────────────────────────────────────
WC_BASE = os.getenv("WP_BASE_URL", "https://sweetsworld.com.au").rstrip("/") + "/wp-json/wc/v3"
WC_CREDS = ("zxyasa", "dOvQ y5z3 oyv6 F7bQ DrEa dbQm")
LS_PRODUCTS_JSONL = Path(__file__).parent.parent.parent.parent / \
    "labs/lightspeed-data-pipeline/data/raw/products.jsonl"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


# ── WooCommerce 拉取 ─────────────────────────────────────────────────────────
def fetch_all_wc_products() -> list[dict]:
    """拉取 WC 全量产品（所有状态）"""
    import base64
    cred = base64.b64encode(f"{WC_CREDS[0]}:{WC_CREDS[1]}".encode()).decode()
    headers = {"Authorization": f"Basic {cred}"}

    all_products = []
    page = 1
    while True:
        params = urllib.parse.urlencode({
            "status": "any", "per_page": 100, "page": page,
            "_fields": "id,sku,name,status,permalink,date_modified"
        })
        req = urllib.request.Request(f"{WC_BASE}/products?{params}", headers=headers)
        resp = urllib.request.urlopen(req, timeout=20)
        items = json.loads(resp.read())
        if not items:
            break
        all_products.extend(items)
        page += 1
        if len(items) < 100:
            break
        time.sleep(0.2)

    return all_products


# ── Lightspeed 读取 ──────────────────────────────────────────────────────────
def load_ls_products() -> dict[str, dict]:
    """读取 Lightspeed 产品，按 SKU 索引（取 parent 产品，去重）"""
    by_sku: dict[str, dict] = {}
    if not LS_PRODUCTS_JSONL.exists():
        print(f"⚠️  Lightspeed 数据文件不存在: {LS_PRODUCTS_JSONL}")
        return by_sku

    with open(LS_PRODUCTS_JSONL) as f:
        for line in f:
            p = json.loads(line)
            sku = p.get("sku", "").strip()
            if not sku:
                continue
            # 同 SKU 多变体时，只要有一个 active 就算 active
            if sku not in by_sku:
                by_sku[sku] = p
            else:
                # 合并：有 active=True 优先
                if p.get("active") and not by_sku[sku].get("active"):
                    by_sku[sku] = p

    return by_sku


# ── URL 验证 ─────────────────────────────────────────────────────────────────
def is_url_dead(url: str) -> tuple[bool, str]:
    """返回 (is_dead, reason)"""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            method="GET"
        )
        resp = urllib.request.urlopen(req, timeout=8)
        final = resp.url.rstrip("/")
        _base = os.getenv("WP_BASE_URL", "https://sweetsworld.com.au").rstrip("/")
        domain = _base
        if final == domain or final == domain.replace("https://", "http://"):
            return True, "redirect→首页"
        return False, ""
    except urllib.error.HTTPError as e:
        return True, f"HTTP {e.code}"
    except Exception as e:
        return True, str(e)[:50]


# ── Telegram 通知 ────────────────────────────────────────────────────────────
def send_telegram(msg: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }).encode()
    req = urllib.request.Request(url, data=data,
                                  headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)


# ── 主逻辑 ───────────────────────────────────────────────────────────────────
def run_health_check(check_urls: bool = False) -> dict[str, Any]:
    print("📦 加载 WooCommerce 产品...")
    wc_products = fetch_all_wc_products()
    print(f"   → {len(wc_products)} 个产品（all statuses）")

    print("📦 加载 Lightspeed 产品...")
    ls_by_sku = load_ls_products()
    print(f"   → {len(ls_by_sku)} 个唯一 SKU")

    # 按 SKU 索引 WC 产品
    wc_by_sku: dict[str, dict] = {}
    wc_no_sku: list[dict] = []
    for p in wc_products:
        sku = p.get("sku", "").strip()
        if sku:
            wc_by_sku[sku] = p
        else:
            wc_no_sku.append(p)

    issues: dict[str, list] = {
        "should_publish": [],    # LS active + WC draft → 应该发布
        "should_unpublish": [],  # LS deleted/inactive + WC publish → 应该下架
        "orphan_wc": [],         # WC 有但 LS 完全没有 → 孤儿产品
        "dead_url": [],          # URL 死链
    }

    print("\n🔍 分析产品状态...")
    for sku, wc in wc_by_sku.items():
        ls = ls_by_sku.get(sku)
        wc_status = wc.get("status", "")
        name = wc.get("name", "")[:50]

        if ls is None:
            # WC 有，LS 没有
            issues["orphan_wc"].append({
                "sku": sku, "name": name,
                "wc_status": wc_status, "wc_id": wc["id"]
            })
        else:
            ls_active = ls.get("active", False)
            ls_deleted = bool(ls.get("deleted_at"))

            if wc_status == "draft" and ls_active and not ls_deleted:
                issues["should_publish"].append({
                    "sku": sku, "name": name,
                    "wc_id": wc["id"], "permalink": wc.get("permalink", ""),
                    "ls_active": ls_active, "ls_deleted_at": ls.get("deleted_at"),
                })
            elif wc_status == "publish" and (ls_deleted or not ls_active):
                issues["should_unpublish"].append({
                    "sku": sku, "name": name,
                    "wc_id": wc["id"], "permalink": wc.get("permalink", ""),
                    "ls_active": ls_active, "ls_deleted_at": ls.get("deleted_at"),
                })

    # URL 死链检查（只检查 publish 状态的产品）
    if check_urls:
        print("\n🔗 检查 URL 死链（published 产品）...")
        published = [p for p in wc_products if p.get("status") == "publish"]
        for i, p in enumerate(published):
            url = p.get("permalink", "")
            if not url:
                continue
            dead, reason = is_url_dead(url)
            if dead:
                issues["dead_url"].append({
                    "sku": p.get("sku", ""), "name": p.get("name", "")[:50],
                    "wc_id": p["id"], "url": url, "reason": reason
                })
            if (i + 1) % 50 == 0:
                print(f"   → {i+1}/{len(published)} checked...")
            time.sleep(0.1)

    return issues


def print_report(issues: dict[str, Any]) -> None:
    should_pub = issues["should_publish"]
    should_unpub = issues["should_unpublish"]
    orphans = issues["orphan_wc"]
    dead = issues["dead_url"]

    print("\n" + "="*60)
    print("📊 产品健康检查报告")
    print("="*60)

    print(f"\n🚨 应发布但在草稿 ({len(should_pub)} 个):")
    for p in should_pub[:20]:
        print(f"   [{p['sku']}] {p['name']}")
    if len(should_pub) > 20:
        print(f"   ... 还有 {len(should_pub)-20} 个")

    print(f"\n⚠️  应下架但仍在售 ({len(should_unpub)} 个):")
    for p in should_unpub[:20]:
        reason = "已删除" if p.get("ls_deleted_at") else "已停用"
        print(f"   [{p['sku']}] {p['name']} ({reason})")
    if len(should_unpub) > 20:
        print(f"   ... 还有 {len(should_unpub)-20} 个")

    print(f"\n❓ WC 有但 LS 无 SKU（孤儿产品）({len(orphans)} 个):")
    print(f"   (仅显示 draft 状态的前10个)")
    draft_orphans = [o for o in orphans if o["wc_status"] == "draft"][:10]
    for p in draft_orphans:
        print(f"   [{p['sku']}] {p['name']} - {p['wc_status']}")

    if dead:
        print(f"\n🔗 URL 死链 ({len(dead)} 个):")
        for p in dead[:10]:
            print(f"   [{p['sku']}] {p['name']} → {p['reason']}")

    print("\n" + "="*60)

    # Telegram 摘要
    msg = (
        f"🏪 <b>{os.getenv('SITE_BRAND', 'SweetsWorld')} 产品健康检查</b>\n\n"
        f"🚨 应发布但草稿: <b>{len(should_pub)}</b> 个\n"
        f"⚠️  应下架但在售: <b>{len(should_unpub)}</b> 个\n"
        f"❓ 孤儿产品(WC有LS无): <b>{len(orphans)}</b> 个\n"
        f"🔗 URL死链: <b>{len(dead)}</b> 个"
    )
    send_telegram(msg)


if __name__ == "__main__":
    check_urls = "--check-urls" in sys.argv
    issues = run_health_check(check_urls=check_urls)
    print_report(issues)

    # 保存结果
    out_path = Path(__file__).parent.parent / "data/product_health_report.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(issues, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n✅ 详细结果已保存: {out_path}")
