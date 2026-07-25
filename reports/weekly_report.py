#!/usr/bin/env python3
"""
Sweetsworld Weekly Report Generator
Runs every Tuesday 14:30 AEST, sends to michael@micleah.com via Brevo SMTP
Archives to reports/weekly/YYYY-WNN.html
"""

import json
import os
import re
import sys
import urllib.request
import urllib.parse
import base64
from datetime import datetime, timedelta
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
REPORTS_DIR = SCRIPT_DIR / "weekly"
ENV_PATH = SCRIPT_DIR.parent / "sites" / "sweetsworld" / ".env"
CREDS_FILE = str(SCRIPT_DIR.parent / "sites" / "sweetsworld" / "gsc_credentials.json")

# Load env
def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    # Also load marketing-copilot env
    mc_env = Path("/Users/michaelzhao/agents/apps/marketing-copilot/sites/sweetsworld/.env")
    if mc_env.exists():
        for line in mc_env.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() not in env:
                    env[k.strip()] = v.strip()
    return env

ENV = load_env()

# Date range: last 7 days (Tuesday to Monday)
TODAY = datetime.now()
END_DATE = (TODAY - timedelta(days=1)).strftime("%Y-%m-%d")  # Yesterday
START_DATE = (TODAY - timedelta(days=7)).strftime("%Y-%m-%d")  # 7 days ago
PREV_END = (TODAY - timedelta(days=8)).strftime("%Y-%m-%d")
PREV_START = (TODAY - timedelta(days=14)).strftime("%Y-%m-%d")
WEEK_NUM = TODAY.strftime("%Y-W%W")


def ga4_query(dimensions, metrics, start=START_DATE, end=END_DATE, au_only=True, order_by_metric=None, limit=20):
    """Query GA4 Data API."""
    try:
        from google.oauth2 import service_account
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            RunReportRequest, DateRange, Dimension, Metric, OrderBy, FilterExpression, Filter
        )
    except ImportError:
        return []

    credentials = service_account.Credentials.from_service_account_file(
        CREDS_FILE, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    client = BetaAnalyticsDataClient(credentials=credentials)

    kwargs = {
        "property": "properties/254089316",
        "date_ranges": [DateRange(start_date=start, end_date=end)],
        "dimensions": [Dimension(name=d) for d in dimensions],
        "metrics": [Metric(name=m) for m in metrics],
        "limit": limit,
    }

    if au_only:
        kwargs["dimension_filter"] = FilterExpression(
            filter=Filter(field_name="country", string_filter=Filter.StringFilter(value="Australia"))
        )

    if order_by_metric:
        kwargs["order_bys"] = [OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_by_metric), desc=True)]
    elif dimensions:
        kwargs["order_bys"] = [OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name=dimensions[0]))]

    response = client.run_report(RunReportRequest(**kwargs))
    rows = []
    for row in response.rows:
        r = {}
        for i, d in enumerate(dimensions):
            r[d] = row.dimension_values[i].value
        for i, m in enumerate(metrics):
            r[m] = row.metric_values[i].value
        rows.append(r)
    return rows


def ga4_event_count(event_name, start=START_DATE, end=END_DATE):
    """Get event count for AU."""
    rows = ga4_query(
        ["country", "eventName"],
        ["eventCount", "totalUsers"],
        start=start, end=end, au_only=False
    )
    for r in rows:
        if r.get("country") == "Australia" and r.get("eventName") == event_name:
            return int(r["eventCount"]), int(r["totalUsers"])
    return 0, 0


def fb_ads_data(start=START_DATE, end=END_DATE):
    """Pull Facebook Ads data."""
    token = ENV.get("META_ACCESS_TOKEN", "")
    if not token:
        return None
    try:
        url = (
            f"https://graph.facebook.com/v19.0/act_{ENV['META_AD_ACCOUNT_ID']}/insights?"
            f"fields=spend,impressions,clicks,actions,action_values"
            f"&time_range={{\"since\":\"{start}\",\"until\":\"{end}\"}}"
            f"&level=account"
            f"&access_token={token}"
        )
        resp = urllib.request.urlopen(url, timeout=15)
        data = json.loads(resp.read())
        if data.get("data"):
            row = data["data"][0]
            actions = {a["action_type"]: a["value"] for a in row.get("actions", [])}
            action_values = {a["action_type"]: float(a["value"]) for a in row.get("action_values", [])}
            return {
                "spend": float(row.get("spend", 0)),
                "clicks": int(row.get("clicks", 0)),
                "atc": int(actions.get("add_to_cart", actions.get("onsite_web_add_to_cart", 0))),
                "purchases": int(actions.get("purchase", actions.get("onsite_web_purchase", 0))),
                "revenue": action_values.get("purchase", action_values.get("onsite_web_purchase", 0)),
            }
    except Exception as e:
        print(f"FB Ads error: {e}")
    return None


def google_ads_data(start=START_DATE, end=END_DATE):
    """Pull Google Ads data."""
    try:
        import yaml
        config = {
            "developer_token": ENV.get("GOOGLE_ADS_DEVELOPER_TOKEN", "8KfC8Mxc74SNrv4FWvreYg"),
            "client_id": ENV.get("GOOGLE_ADS_CLIENT_ID", ""),
            "client_secret": ENV.get("GOOGLE_ADS_CLIENT_SECRET", ""),
            "refresh_token": ENV.get("GOOGLE_ADS_REFRESH_TOKEN", ""),
            "use_proto_plus": True,
        }
        with open("/tmp/google-ads-report.yaml", "w") as f:
            yaml.dump(config, f)

        from google.ads.googleads.client import GoogleAdsClient
        client = GoogleAdsClient.load_from_storage("/tmp/google-ads-report.yaml")
        ga_service = client.get_service("GoogleAdsService")

        query = f"""
        SELECT campaign.name, campaign.status,
               metrics.cost_micros, metrics.clicks, metrics.impressions,
               metrics.conversions, metrics.conversions_value
        FROM campaign
        WHERE campaign.status = 'ENABLED'
          AND segments.date BETWEEN '{start}' AND '{end}'
        """
        response = ga_service.search(customer_id="3729934200", query=query)
        total = {"spend": 0, "clicks": 0, "conversions": 0, "revenue": 0}
        for row in response:
            total["spend"] += row.metrics.cost_micros / 1_000_000
            total["clicks"] += row.metrics.clicks
            total["conversions"] += row.metrics.conversions
            total["revenue"] += row.metrics.conversions_value
        return total
    except Exception as e:
        print(f"Google Ads error: {e}")
    return None


def wc_orders(start=START_DATE, end=END_DATE):
    """Get WooCommerce order stats."""
    wp_auth = base64.b64encode(
        f"{ENV.get('WP_USERNAME', 'zxyasa')}:{ENV.get('WP_APP_PASSWORD', '')}".encode()
    ).decode()

    proxy_domains = ['@bigw.com', '@kogan.com', '@ebay.com', '@members.ebay',
                     '@amazon.com', '@catch.com', '@mydeal.com', '@edm.com', 'dispatch_']

    all_orders = []
    page = 1
    while page <= 5:
        url = (
            f"https://sweetsworld.com.au/wp-json/wc/v3/orders?"
            f"status=completed,processing&per_page=100&page={page}"
            f"&after={start}T00:00:00&before={end}T23:59:59"
        )
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {wp_auth}"})
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            orders = json.loads(resp.read())
            if not orders:
                break
            all_orders.extend(orders)
            page += 1
        except:
            break

    direct = []
    platform = []
    for o in all_orders:
        email = o.get("billing", {}).get("email", "").lower()
        subtotal = sum(float(li.get("subtotal", 0)) for li in o.get("line_items", []))
        if subtotal <= 0:
            continue
        is_proxy = any(d in email for d in proxy_domains)
        if is_proxy:
            platform.append(subtotal)
        else:
            direct.append(subtotal)

    return {
        "direct_count": len(direct),
        "direct_total": sum(direct),
        "direct_aov": sum(direct) / len(direct) if direct else 0,
        "platform_count": len(platform),
        "platform_total": sum(platform),
    }


def generate_report():
    """Generate the weekly report HTML."""
    print(f"Generating report for {START_DATE} to {END_DATE}...")

    # GA4 data
    daily = ga4_query(["date"], ["sessions", "activeUsers", "bounceRate", "averageSessionDuration"])
    sources = ga4_query(["sessionDefaultChannelGroup"], ["sessions"], order_by_metric="sessions", limit=8)
    devices = ga4_query(["deviceCategory"], ["sessions", "bounceRate"], order_by_metric="sessions")

    # Previous week for comparison
    daily_prev = ga4_query(["date"], ["sessions"], start=PREV_START, end=PREV_END)
    total_sessions = sum(int(r["sessions"]) for r in daily)
    total_sessions_prev = sum(int(r["sessions"]) for r in daily_prev)
    sessions_change = ((total_sessions - total_sessions_prev) / total_sessions_prev * 100) if total_sessions_prev > 0 else 0

    # Funnel
    funnel = {}
    for event in ["view_item", "add_to_cart", "begin_checkout", "purchase"]:
        count, users = ga4_event_count(event)
        funnel[event] = {"count": count, "users": users}

    # Ads
    fb = fb_ads_data()
    gads = google_ads_data()

    # WooCommerce
    wc = wc_orders()
    wc_prev = wc_orders(PREV_START, PREV_END)

    # Goals
    fb_start = "2026-04-11"
    gads_start = "2026-04-15"
    fb_days = (TODAY - datetime.strptime(fb_start, "%Y-%m-%d")).days
    gads_days = (TODAY - datetime.strptime(gads_start, "%Y-%m-%d")).days

    total_ad_spend = (fb["spend"] if fb else 0) + (gads["spend"] if gads else 0)
    total_ad_revenue = (fb["revenue"] if fb else 0) + (gads["revenue"] if gads else 0)
    total_roas = total_ad_revenue / total_ad_spend if total_ad_spend > 0 else 0
    total_purchases_ads = (fb["purchases"] if fb else 0) + (int(gads["conversions"]) if gads else 0)

    # Funnel rates
    view_users = funnel.get("view_item", {}).get("users", 0)
    atc_users = funnel.get("add_to_cart", {}).get("users", 0)
    checkout_users = funnel.get("begin_checkout", {}).get("users", 0)
    purchase_users = funnel.get("purchase", {}).get("users", 0)

    atc_rate = (atc_users / view_users * 100) if view_users > 0 else 0
    checkout_rate = (checkout_users / atc_users * 100) if atc_users > 0 else 0
    purchase_rate = (purchase_users / checkout_users * 100) if checkout_users > 0 else 0

    def rate_class(val, good_min, warn_min):
        if val >= good_min: return "metric-good"
        if val >= warn_min: return "metric-neutral"
        return "metric-bad"

    def change_str(curr, prev):
        if prev == 0: return "—"
        pct = (curr - prev) / prev * 100
        cls = "metric-good" if pct > 0 else "metric-bad" if pct < 0 else ""
        sign = "+" if pct > 0 else ""
        return f'<span class="{cls}">{sign}{pct:.0f}%</span>'

    # Monthly revenue estimate
    monthly_direct = wc["direct_total"] / 7 * 30

    html = f"""<html>
<head>
<style>
body {{ font-family: Arial, sans-serif; max-width: 720px; margin: 0 auto; padding: 20px; color: #333; }}
h1 {{ color: #c0392b; font-size: 22px; border-bottom: 2px solid #c0392b; padding-bottom: 8px; }}
h2 {{ color: #2c3e50; font-size: 16px; margin-top: 24px; }}
table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 13px; }}
th {{ background: #f8f8f8; text-align: left; padding: 6px 8px; border-bottom: 2px solid #ddd; }}
td {{ padding: 6px 8px; border-bottom: 1px solid #eee; }}
.metric-good {{ color: #27ae60; font-weight: bold; }}
.metric-bad {{ color: #e74c3c; font-weight: bold; }}
.metric-neutral {{ color: #f39c12; font-weight: bold; }}
.box {{ padding: 12px 16px; margin: 12px 0; border-radius: 4px; border-left: 4px solid; }}
.box-info {{ background: #f0f7ff; border-color: #3498db; }}
.box-alert {{ background: #fff5f5; border-color: #e74c3c; }}
.box-success {{ background: #f0fff4; border-color: #27ae60; }}
.footer {{ margin-top: 30px; padding-top: 16px; border-top: 1px solid #ddd; font-size: 11px; color: #999; }}
</style>
</head>
<body>

<h1>Sweetsworld Weekly Report</h1>
<p style="color:#888; font-size:12px;">Week: {START_DATE} — {END_DATE} | Generated: {TODAY.strftime("%Y-%m-%d %H:%M")} AEST</p>

<h2>0. Goals Tracker</h2>
<table>
<tr><th>Timeframe</th><th>Goal</th><th>Current</th><th>Target</th><th>Status</th></tr>
<tr><td rowspan="3"><strong>Short (4 wk)</strong></td><td>Ad ROAS ≥ 1.0x</td><td>{total_roas:.2f}x</td><td>1.0x</td><td class="{rate_class(total_roas, 1.0, 0.8)}">{"✅" if total_roas >= 1.0 else "❌"}</td></tr>
<tr><td>Cart→Checkout ≥ 30%</td><td>{checkout_rate:.1f}%</td><td>30%</td><td class="{rate_class(checkout_rate, 30, 20)}">{"✅" if checkout_rate >= 30 else "❌"}</td></tr>
<tr><td>Newsletter ≥ 50</td><td>1</td><td>50</td><td class="metric-bad">❌</td></tr>
<tr><td rowspan="3"><strong>Mid (3 mo)</strong></td><td>Direct revenue $5K/mo</td><td>${monthly_direct:.0f}/mo est</td><td>$5,000</td><td class="{rate_class(monthly_direct, 5000, 2000)}">{"✅" if monthly_direct >= 5000 else "❌"}</td></tr>
<tr><td>ROAS ≥ 2.0x</td><td>{total_roas:.2f}x</td><td>2.0x</td><td class="{rate_class(total_roas, 2.0, 1.0)}">{"✅" if total_roas >= 2.0 else "❌"}</td></tr>
<tr><td>AU 200 sessions/day</td><td>{total_sessions/7:.0f}/day</td><td>200</td><td class="{rate_class(total_sessions/7, 200, 120)}">{"✅" if total_sessions/7 >= 200 else "⚠️"}</td></tr>
<tr><td rowspan="2"><strong>Long (12 mo)</strong></td><td>Direct revenue $20K/mo</td><td>${monthly_direct:.0f}/mo est</td><td>$20,000</td><td class="metric-bad">❌</td></tr>
<tr><td>AOV $65+</td><td>${wc['direct_aov']:.2f}</td><td>$65</td><td class="{rate_class(wc['direct_aov'], 65, 50)}">{"✅" if wc['direct_aov'] >= 65 else "⚠️"}</td></tr>
</table>

<h2>1. Traffic — Australia Only</h2>
<div class="box box-info"><strong>AU Sessions: {total_sessions}</strong> ({change_str(total_sessions, total_sessions_prev)} vs last week) | Daily avg: {total_sessions/7:.0f}</div>
<table>
<tr><th>Date</th><th>Sessions</th><th>Users</th><th>Bounce</th><th>Avg Duration</th></tr>"""

    for r in daily:
        html += f"""
<tr><td>{r['date']}</td><td>{r['sessions']}</td><td>{r['activeUsers']}</td><td>{float(r['bounceRate'])*100:.1f}%</td><td>{float(r['averageSessionDuration']):.0f}s</td></tr>"""

    html += f"""
<tr style="font-weight:bold; background:#f8f8f8;"><td>Total</td><td>{total_sessions}</td><td>—</td><td>—</td><td>—</td></tr>
</table>

<h2>2. Traffic Sources (AU)</h2>
<table>
<tr><th>Source</th><th>Sessions</th><th>%</th></tr>"""

    for r in sources:
        pct = int(r["sessions"]) / total_sessions * 100 if total_sessions > 0 else 0
        html += f"""
<tr><td>{r['sessionDefaultChannelGroup']}</td><td>{r['sessions']}</td><td>{pct:.0f}%</td></tr>"""

    html += f"""
</table>

<h2>3. Devices (AU)</h2>
<table>
<tr><th>Device</th><th>Sessions</th><th>Bounce Rate</th></tr>"""

    for r in devices:
        html += f"""
<tr><td>{r['deviceCategory']}</td><td>{r['sessions']}</td><td>{float(r['bounceRate'])*100:.1f}%</td></tr>"""

    html += f"""
</table>

<h2>4. Ecommerce Funnel (AU)</h2>
<table>
<tr><th>Stage</th><th>Events</th><th>Users</th><th>Rate</th><th>Benchmark</th><th>Status</th></tr>
<tr><td>View Product</td><td>{funnel.get('view_item',{}).get('count',0)}</td><td>{view_users}</td><td>—</td><td>—</td><td>—</td></tr>
<tr><td>Add to Cart</td><td>{funnel.get('add_to_cart',{}).get('count',0)}</td><td>{atc_users}</td><td class="{rate_class(atc_rate, 10, 7)}">{atc_rate:.1f}%</td><td>7-8%</td><td>{"✅" if atc_rate >= 7 else "❌"}</td></tr>
<tr><td>Begin Checkout</td><td>{funnel.get('begin_checkout',{}).get('count',0)}</td><td>{checkout_users}</td><td class="{rate_class(checkout_rate, 30, 20)}">{checkout_rate:.1f}%</td><td>30-40%</td><td>{"✅" if checkout_rate >= 30 else "❌"}</td></tr>
<tr><td>Purchase</td><td>{funnel.get('purchase',{}).get('count',0)}</td><td>{purchase_users}</td><td class="{rate_class(purchase_rate, 40, 25)}">{purchase_rate:.1f}%</td><td>40-50%</td><td>{"✅" if purchase_rate >= 40 else "⚠️"}</td></tr>
</table>"""

    if checkout_rate < 30 and atc_users > 0:
        lost = atc_users - checkout_users
        html += f"""
<div class="box box-alert"><strong>Bottleneck:</strong> {atc_users} users added to cart → only {checkout_users} began checkout ({checkout_rate:.0f}%). {lost} potential customers lost.</div>"""

    # Advertising
    html += f"""
<h2>5. Advertising</h2>
<table>
<tr><th>Platform</th><th>Start</th><th>Days</th><th>Spend</th><th>Clicks</th><th>ATC</th><th>Purchases</th><th>Revenue</th><th>ROAS</th></tr>"""

    if fb:
        fb_roas = fb["revenue"] / fb["spend"] if fb["spend"] > 0 else 0
        html += f"""
<tr><td>Facebook</td><td>{fb_start}</td><td>{fb_days}</td><td>${fb['spend']:.2f}</td><td>{fb['clicks']}</td><td>{fb['atc']}</td><td>{fb['purchases']}</td><td>${fb['revenue']:.2f}</td><td class="{rate_class(fb_roas, 1.0, 0.5)}">{fb_roas:.2f}x</td></tr>"""

    if gads:
        g_roas = gads["revenue"] / gads["spend"] if gads["spend"] > 0 else 0
        html += f"""
<tr><td>Google PMax</td><td>{gads_start}</td><td>{gads_days}</td><td>${gads['spend']:.2f}</td><td>{gads['clicks']}</td><td>—</td><td>{int(gads['conversions'])}</td><td>${gads['revenue']:.2f}</td><td class="{rate_class(g_roas, 1.0, 0.5)}">{g_roas:.2f}x</td></tr>"""

    html += f"""
<tr style="font-weight:bold; background:#f8f8f8;"><td>Total</td><td></td><td></td><td>${total_ad_spend:.2f}</td><td></td><td></td><td>{total_purchases_ads}</td><td>${total_ad_revenue:.2f}</td><td class="{rate_class(total_roas, 1.0, 0.5)}">{total_roas:.2f}x</td></tr>
</table>

<h2>6. WooCommerce Orders</h2>
<table>
<tr><th>Metric</th><th>This Week</th><th>Last Week</th><th>Change</th></tr>
<tr><td>Direct Orders</td><td>{wc['direct_count']}</td><td>{wc_prev['direct_count']}</td><td>{change_str(wc['direct_count'], wc_prev['direct_count'])}</td></tr>
<tr><td>Platform Orders</td><td>{wc['platform_count']}</td><td>{wc_prev['platform_count']}</td><td>{change_str(wc['platform_count'], wc_prev['platform_count'])}</td></tr>
<tr><td>Direct AOV</td><td>${wc['direct_aov']:.2f}</td><td>${wc_prev['direct_aov']:.2f}</td><td>{change_str(wc['direct_aov'], wc_prev['direct_aov'])}</td></tr>
<tr><td>Direct Revenue</td><td>${wc['direct_total']:.2f}</td><td>${wc_prev['direct_total']:.2f}</td><td>{change_str(wc['direct_total'], wc_prev['direct_total'])}</td></tr>
</table>

<h2>7. Change Log</h2>
<div class="box box-success">
<em>Auto-populated from memory files. Manual entries can be added below.</em>
</div>

<h2>8. Next Week Focus</h2>
<div class="box box-alert">
<em>Review and update during weekly planning.</em>
</div>

<div class="footer">
Generated by AI Growth Agent | Sweetsworld.com.au<br>
Data: GA4 (AU only), Meta Ads API, Google Ads API, WooCommerce<br>
Report archived: reports/weekly/{WEEK_NUM}.html
</div>

</body>
</html>"""

    return html


def send_email(html, to="michael@micleah.com"):
    """Send via Brevo REST API (transactional). SMTP retired 2026-07 (Brevo deactivated
    SMTP keys); the whole SW email stack runs on the Brevo REST API + xkeysib key."""
    api_key = ENV.get("BREVO_API_KEY", "")
    if not api_key:
        print("❌ No BREVO_API_KEY in env (checked seo-agent + marketing-copilot .env)")
        return False
    payload = json.dumps({
        "sender": {"name": "Sweetsworld AI", "email": "hello@sweetsworld.com.au"},
        "to": [{"email": to}],
        "subject": f"Sweetsworld Weekly Report — {START_DATE} to {END_DATE}",
        "htmlContent": html,
    }).encode()
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email", data=payload,
        headers={"api-key": api_key, "content-type": "application/json",
                 "accept": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        print(f"✅ Email sent to {to} (Brevo REST, HTTP {resp.status})")
        return True
    except Exception as e:
        body = e.read().decode()[:200] if hasattr(e, "read") else ""
        print(f"❌ Brevo REST send failed: {e} {body}")
        return False


def main():
    # Generate
    html = generate_report()

    # Archive
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = REPORTS_DIR / f"{WEEK_NUM}.html"
    archive_path.write_text(html)
    print(f"✅ Archived: {archive_path}")

    # Send
    if "--dry-run" not in sys.argv:
        send_email(html)
    else:
        print("Dry run — email not sent")
        # Open in browser for preview
        import subprocess
        subprocess.run(["open", str(archive_path)])


if __name__ == "__main__":
    main()
