"""
Product URL Health Check
每次运行扫描 products.json 里的所有产品 URL，诊断问题类型并推送 Telegram 报警。

问题等级：
  🚨 CRITICAL  — 301 跳首页（Rank Math/Yoast 错误 redirect，直接影响销售）
  ⚠️  WARNING   — 301 跳其他页面（slug 可能变了）
  ❌  ERROR     — 404 / 连接失败
  ✅  OK        — 正常

用法：
  python src/product_url_health_check.py              # 扫描全部
  python src/product_url_health_check.py --sample 50 # 抽样 50 条
  python src/product_url_health_check.py --notify     # 扫描 + 推送 Telegram
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

import requests

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_FILE = PROJECT_ROOT / "data" / "products.json"

import os as _os
SITE_DOMAIN = _os.getenv("WP_BASE_URL", "https://sweetsworld.com.au").rstrip("/").split("//")[-1]
HOMEPAGE_URLS = {
    f"https://{SITE_DOMAIN}",
    f"https://{SITE_DOMAIN}/",
    f"http://{SITE_DOMAIN}",
    f"http://{SITE_DOMAIN}/",
}

# 每批请求之间的间隔（秒），避免触发服务器限速
REQUEST_DELAY = 0.3


def _classify(url: str, timeout: int = 8) -> Tuple[str, str, str]:
    """
    检测单条 URL，返回 (level, reason, final_url)。
    level: 'ok' | 'critical' | 'warning' | 'error'
    """
    try:
        resp = requests.get(url, allow_redirects=True, timeout=timeout,
                            headers={"User-Agent": f"Mozilla/5.0 (compatible; {_os.getenv('SITE_BRAND', 'SweetsWorld')}Bot/1.0)"})
        final = resp.url.rstrip("/")
        final_norm = final if final.endswith("/") else final + "/"
        status = resp.status_code

        if status >= 400:
            return "error", f"HTTP {status}", final

        # 落地是首页 → 最严重
        if final.rstrip("/") in {u.rstrip("/") for u in HOMEPAGE_URLS}:
            # 看是直接返回还是经过跳转
            if resp.history:
                codes = " → ".join(str(r.status_code) for r in resp.history)
                via = resp.history[-1].headers.get("location", "?")
                return "critical", f"重定向到首页 ({codes}，经过: {via})", final
            return "critical", "直接返回首页内容（可能 404 被吸收）", final

        # 落地 URL 和原始 URL 不同 → slug/路径变了
        if final.rstrip("/") != url.rstrip("/"):
            return "warning", f"重定向到其他页面: {final}", final

        return "ok", "", final

    except requests.exceptions.ConnectionError:
        return "error", "连接失败", ""
    except requests.exceptions.Timeout:
        return "error", "请求超时", ""
    except Exception as exc:
        return "error", str(exc)[:100], ""


def run_check(sample: int | None = None, notify: bool = False) -> Dict:
    with open(PRODUCTS_FILE) as f:
        data = json.load(f)
    products = data["products"]

    if sample:
        import random
        products = random.sample(products, min(sample, len(products)))

    total = len(products)
    results: Dict[str, List[dict]] = {"critical": [], "warning": [], "error": [], "ok": []}

    logger.info(f"扫描 {total} 个产品 URL...\n")

    for i, product in enumerate(products, 1):
        url = product.get("url", "")
        name = product.get("product_name", "?")
        if not url:
            continue

        level, reason, final_url = _classify(url)
        entry = {"name": name, "url": url, "reason": reason, "final_url": final_url}
        results[level].append(entry)

        icon = {"ok": "✅", "critical": "🚨", "warning": "⚠️", "error": "❌"}[level]
        if level != "ok":
            logger.info(f"{icon} [{i}/{total}] {name}")
            logger.info(f"   URL: {url}")
            logger.info(f"   问题: {reason}\n")
        else:
            if i % 50 == 0:
                logger.info(f"   ... {i}/{total} 已完成")

        time.sleep(REQUEST_DELAY)

    # 汇总
    n_critical = len(results["critical"])
    n_warning = len(results["warning"])
    n_error = len(results["error"])
    n_ok = len(results["ok"])

    logger.info("\n" + "=" * 50)
    logger.info(f"扫描完成：共 {total} 个产品")
    logger.info(f"  🚨 CRITICAL（影响销售）: {n_critical}")
    logger.info(f"  ⚠️  WARNING（需确认）:   {n_warning}")
    logger.info(f"  ❌  ERROR（连接失败）:   {n_error}")
    logger.info(f"  ✅  OK:                  {n_ok}")

    if notify and (n_critical + n_warning + n_error > 0):
        _send_telegram_alert(results, total)

    return results


def _send_telegram_alert(results: Dict, total: int) -> None:
    """推送 Telegram 报警。"""
    import os
    # 优先读 .env
    env_path = PROJECT_ROOT / ".env"
    token, chat_id = "", ""
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                token = line.split("=", 1)[1].strip()
            elif line.startswith("TELEGRAM_CHAT_ID="):
                chat_id = line.split("=", 1)[1].strip()

    # fallback 到环境变量
    token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        logger.warning("Telegram 未配置，跳过推送")
        return

    lines = [f"🏪 *{_os.getenv('SITE_BRAND', 'SweetsWorld')} 产品 URL 健康检查* — 共 {total} 个产品\n"]

    if results["critical"]:
        lines.append(f"🚨 *CRITICAL — 影响销售（{len(results['critical'])} 个）*")
        for item in results["critical"][:10]:
            lines.append(f"• {item['name']}")
            lines.append(f"  `{item['url']}`")
            lines.append(f"  原因: {item['reason']}")
        if len(results["critical"]) > 10:
            lines.append(f"  ...还有 {len(results['critical']) - 10} 个")

    if results["warning"]:
        lines.append(f"\n⚠️ *WARNING — 需确认（{len(results['warning'])} 个）*")
        for item in results["warning"][:5]:
            lines.append(f"• {item['name']}: {item['reason']}")

    if results["error"]:
        lines.append(f"\n❌ *ERROR — 连接失败（{len(results['error'])} 个）*")
        for item in results["error"][:5]:
            lines.append(f"• {item['name']}: {item['reason']}")

    lines.append(f"\n✅ 正常: {len(results['ok'])} 个")

    text = "\n".join(lines)

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown",
                  "disable_web_page_preview": True},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("✅ Telegram 报警已推送")
    except Exception as exc:
        logger.error(f"Telegram 推送失败: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Product URL Health Check")
    parser.add_argument("--sample", type=int, default=None, help="抽样 N 个产品（不填则全部扫描）")
    parser.add_argument("--notify", action="store_true", help="发现问题时推送 Telegram")
    args = parser.parse_args()

    results = run_check(sample=args.sample, notify=args.notify)

    # 有 critical 问题时非零退出码，方便 cron 感知
    if results["critical"]:
        sys.exit(2)
    elif results["warning"] or results["error"]:
        sys.exit(1)
