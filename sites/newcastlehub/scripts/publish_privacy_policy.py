#!/usr/bin/env python3
"""
Publish Privacy Policy to Newcastle Hub WordPress (page ID 3).

Steps:
  1. Fetch current page content and save snapshot
  2. Write new Privacy Policy HTML
  3. Publish via WP REST API
  4. Verify and report
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

# ── Config ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / ".env"

def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip()
    return env

env = load_env(ENV_FILE)
WP_BASE_URL   = env["WP_BASE_URL"].rstrip("/")
WP_USERNAME   = env["WP_USERNAME"]
WP_APP_PASSWORD = env["WP_APP_PASSWORD"]
AUTH = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
PAGE_ID = 3
SNAPSHOT_PATH = BASE_DIR / "snapshots" / "privacy_policy_3_pre_rewrite.json"

# ── Privacy Policy HTML ────────────────────────────────────────────────────
PRIVACY_POLICY_HTML = """<h2>Privacy Policy</h2>

<p><strong>Effective Date:</strong> April 2026<br>
<strong>Last Updated:</strong> April 2026</p>

<p>Newcastle Hub ("we", "us", or "our") is committed to protecting your personal information and your right to privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you visit our website at <a href="https://newcastlehub.info">newcastlehub.info</a> or engage our services.</p>

<p>We operate in accordance with the <em>Privacy Act 1988</em> (Cth) and the Australian Privacy Principles (APPs) contained in Schedule 1 of that Act.</p>

<p>Please read this policy carefully. If you disagree with its terms, please discontinue use of our site and services.</p>

<hr>

<h2>1. Who We Are</h2>

<p>Newcastle Hub is a local digital services business based in Newcastle / East Maitland, NSW, Australia.</p>

<ul>
  <li><strong>Business name:</strong> Newcastle Hub</li>
  <li><strong>Address:</strong> Shop 1089, Stockland Greenhills, East Maitland NSW 2323</li>
  <li><strong>Email:</strong> <a href="mailto:hello@newcastlehub.info">hello@newcastlehub.info</a></li>
  <li><strong>Website:</strong> <a href="https://newcastlehub.info">https://newcastlehub.info</a></li>
</ul>

<p>We provide web design, digital marketing, point-of-sale (POS) systems, web hosting, and AI implementation services to small and medium-sized businesses.</p>

<hr>

<h2>2. Information We Collect</h2>

<p>We collect personal information that you voluntarily provide to us, as well as information collected automatically when you visit our website.</p>

<h3>2.1 Information You Provide</h3>

<p>When you contact us, request a quote, or engage our services, we may collect:</p>

<ul>
  <li>Full name</li>
  <li>Email address</li>
  <li>Phone number</li>
  <li>Business name and address</li>
  <li>Details of your enquiry or project requirements</li>
  <li>Payment information (processed securely through third-party providers — we do not store card numbers)</li>
</ul>

<h3>2.2 Information Collected Automatically</h3>

<p>When you visit our website, certain information is collected automatically, including:</p>

<ul>
  <li>IP address and general geographic location</li>
  <li>Browser type and version</li>
  <li>Operating system</li>
  <li>Pages visited and time spent on each page</li>
  <li>Referring URL</li>
  <li>Date and time of your visit</li>
  <li>Cookie identifiers (see Section 6 — Cookie Policy)</li>
</ul>

<p>This data is collected through cookies and analytics tools (see below) and is used in aggregate or anonymised form where possible.</p>

<hr>

<h2>3. How We Use Your Information</h2>

<p>We use the personal information we collect for the following purposes:</p>

<ul>
  <li><strong>Providing services:</strong> To fulfil and manage the services you have requested, including web design, hosting, digital marketing, POS configuration, and AI implementation.</li>
  <li><strong>Responding to enquiries:</strong> To contact you in response to enquiries, quote requests, or support tickets.</li>
  <li><strong>Invoicing and payments:</strong> To send invoices and process payments for services rendered.</li>
  <li><strong>Improving our website:</strong> To analyse usage patterns, identify issues, and improve the performance and content of our website.</li>
  <li><strong>Marketing communications:</strong> To send you information about our services, promotions, or industry news that may be of interest to you. You may opt out at any time (see Section 3.1).</li>
  <li><strong>Legal compliance:</strong> To comply with applicable laws, regulations, and legal obligations.</li>
</ul>

<p>We will only use your personal information for the purposes for which it was collected, or for a directly related purpose, unless you have consented otherwise or we are required by law to do so.</p>

<h3>3.1 Opting Out of Marketing Communications</h3>

<p>If you no longer wish to receive marketing communications from us, you may opt out at any time by:</p>

<ul>
  <li>Clicking the "unsubscribe" link in any marketing email we send; or</li>
  <li>Contacting us directly at <a href="mailto:hello@newcastlehub.info">hello@newcastlehub.info</a>.</li>
</ul>

<p>We will action your opt-out request promptly. Please note that even if you opt out of marketing emails, we may still contact you regarding your existing service relationship (e.g. invoices, project updates, support).</p>

<hr>

<h2>4. Disclosure to Third Parties</h2>

<p>We do not sell, trade, or rent your personal information to third parties.</p>

<p>We may share your information with trusted third-party service providers who assist us in operating our website and delivering our services, including:</p>

<ul>
  <li><strong>Google Analytics:</strong> For website traffic analysis. Google may process your data in accordance with its own privacy policy. You can opt out of Google Analytics tracking at <a href="https://tools.google.com/dlpage/gaoptout" target="_blank" rel="noopener noreferrer">https://tools.google.com/dlpage/gaoptout</a>.</li>
  <li><strong>Square:</strong> For point-of-sale payment processing. Square processes payment data in accordance with PCI-DSS standards and its own privacy policy (<a href="https://squareup.com/au/en/legal/general/privacy" target="_blank" rel="noopener noreferrer">squareup.com/au/en/legal/general/privacy</a>).</li>
  <li><strong>Email service providers:</strong> We use third-party email platforms to send transactional and marketing emails. These providers are required to handle your data securely and in accordance with applicable privacy laws.</li>
  <li><strong>Web hosting providers:</strong> Our website and some client sites are hosted on third-party servers. Hosting providers may have access to server logs which can contain IP addresses and usage data.</li>
</ul>

<p>All third-party service providers are contractually obligated to keep your information confidential and to use it only to perform the services they have been engaged to provide.</p>

<p>We may also disclose your personal information where required or permitted by law, including to government agencies, courts, or law enforcement bodies.</p>

<hr>

<h2>5. Cross-Border Disclosure</h2>

<p>Some of our third-party service providers (including Google and Square) are based outside Australia and may store or process your data overseas, including in the United States. By providing us with your personal information and using our services, you consent to this potential cross-border transfer.</p>

<p>We take reasonable steps to ensure that any overseas recipients handle your personal information in a way that is consistent with the Australian Privacy Principles.</p>

<hr>

<h2>6. Cookie Policy</h2>

<h3>6.1 What Are Cookies?</h3>

<p>Cookies are small text files placed on your device by websites you visit. They are widely used to make websites work more efficiently and to provide analytical information to website owners.</p>

<h3>6.2 Cookies We Use</h3>

<p>Our website uses the following types of cookies:</p>

<ul>
  <li><strong>Essential cookies:</strong> Required for the website to function properly (e.g. session management, security). These cannot be disabled.</li>
  <li><strong>Analytics cookies:</strong> Set by Google Analytics to help us understand how visitors use our site (e.g. pages viewed, time on site, traffic sources). This data is aggregated and anonymised where possible.</li>
  <li><strong>Preference cookies:</strong> Used to remember your settings and preferences to improve your experience on return visits.</li>
</ul>

<h3>6.3 How to Disable Cookies</h3>

<p>You can control and/or delete cookies through your browser settings. Most browsers allow you to:</p>

<ul>
  <li>View what cookies are set and delete them individually</li>
  <li>Block cookies from specific websites</li>
  <li>Block all third-party cookies</li>
  <li>Block all cookies (note: this may impact website functionality)</li>
</ul>

<p>For instructions specific to your browser, visit <a href="https://www.allaboutcookies.org" target="_blank" rel="noopener noreferrer">www.allaboutcookies.org</a>.</p>

<p>To opt out of Google Analytics specifically, install the Google Analytics Opt-out Browser Add-on: <a href="https://tools.google.com/dlpage/gaoptout" target="_blank" rel="noopener noreferrer">tools.google.com/dlpage/gaoptout</a>.</p>

<hr>

<h2>7. Data Security</h2>

<p>We take reasonable steps to protect the personal information we hold from misuse, interference, and loss, and from unauthorised access, modification, or disclosure. These steps include:</p>

<ul>
  <li>Using HTTPS encryption for all data transmitted through our website</li>
  <li>Restricting access to personal information to authorised personnel only</li>
  <li>Using secure, password-protected systems</li>
  <li>Regularly reviewing and updating our security practices</li>
</ul>

<p>While we take all reasonable precautions, no method of electronic transmission or storage is 100% secure. We cannot guarantee the absolute security of your personal information.</p>

<p>If we become aware of a data breach that is likely to result in serious harm to any individuals, we will notify affected individuals and the Office of the Australian Information Commissioner (OAIC) in accordance with the Notifiable Data Breaches (NDB) scheme under the Privacy Act 1988.</p>

<hr>

<h2>8. Your Privacy Rights</h2>

<p>Under the Privacy Act 1988 and Australian Privacy Principles, you have the following rights regarding your personal information:</p>

<h3>8.1 Right to Access</h3>

<p>You may request access to the personal information we hold about you. We will respond to your request within 30 days and, where access is granted, provide the information in a clear and understandable format.</p>

<h3>8.2 Right to Correction</h3>

<p>If you believe personal information we hold about you is inaccurate, out of date, incomplete, irrelevant, or misleading, you may request that we correct it. We will take reasonable steps to correct the information and notify any third parties to whom we have disclosed it where relevant.</p>

<h3>8.3 Right to Deletion</h3>

<p>In certain circumstances, you may request that we delete personal information we hold about you (e.g. where it is no longer needed for the purpose it was collected). We will consider all such requests and will comply unless we are required by law to retain the information.</p>

<h3>8.4 How to Submit a Request</h3>

<p>To exercise any of these rights, please contact us at:</p>

<p><strong>Email:</strong> <a href="mailto:hello@newcastlehub.info">hello@newcastlehub.info</a><br>
<strong>Address:</strong> Shop 1089, Stockland Greenhills, East Maitland NSW 2323</p>

<p>We may need to verify your identity before processing your request. We will not charge you for making a request unless the request is clearly excessive or unreasonable.</p>

<p>If you are unhappy with how we handle your request, you may lodge a complaint with the Office of the Australian Information Commissioner (OAIC):</p>

<ul>
  <li><strong>Website:</strong> <a href="https://www.oaic.gov.au" target="_blank" rel="noopener noreferrer">www.oaic.gov.au</a></li>
  <li><strong>Phone:</strong> 1300 363 992</li>
</ul>

<hr>

<h2>9. Links to Other Websites</h2>

<p>Our website may contain links to third-party websites, plugins, and applications. Clicking on those links or enabling those connections may allow third parties to collect or share data about you. We do not control these third-party websites and are not responsible for their privacy practices or content.</p>

<p>We encourage you to read the privacy policy of every website you visit.</p>

<hr>

<h2>10. Children's Privacy</h2>

<p>Our website and services are not directed to individuals under the age of 18. We do not knowingly collect personal information from children. If you are a parent or guardian and believe your child has provided us with personal information, please contact us at <a href="mailto:hello@newcastlehub.info">hello@newcastlehub.info</a> and we will delete that information.</p>

<hr>

<h2>11. Changes to This Privacy Policy</h2>

<p>We may update this Privacy Policy from time to time to reflect changes in our practices, services, or legal obligations. We will notify you of any significant changes by updating the "Last Updated" date at the top of this page.</p>

<p>We encourage you to review this Privacy Policy periodically to stay informed about how we are protecting your information.</p>

<hr>

<h2>12. Contact Us</h2>

<p>If you have any questions, concerns, or complaints about this Privacy Policy or our privacy practices, please contact us:</p>

<ul>
  <li><strong>Email:</strong> <a href="mailto:hello@newcastlehub.info">hello@newcastlehub.info</a></li>
  <li><strong>Address:</strong> Shop 1089, Stockland Greenhills, East Maitland NSW 2323</li>
  <li><strong>Website:</strong> <a href="https://newcastlehub.info/contact">https://newcastlehub.info/contact</a></li>
</ul>

<p>We will respond to all privacy enquiries within 30 days.</p>

<hr>

<p><em>This Privacy Policy is governed by the laws of New South Wales, Australia, and the Commonwealth of Australia. Any disputes relating to this policy shall be subject to the exclusive jurisdiction of the courts of New South Wales.</em></p>"""


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    api_base = f"{WP_BASE_URL}/wp-json/wp/v2"

    # Step 1: Fetch current page and save snapshot
    print(f"[1/4] Fetching current page ID {PAGE_ID}...")
    resp = requests.get(
        f"{api_base}/pages/{PAGE_ID}",
        params={"context": "edit"},
        auth=AUTH,
        timeout=30,
    )
    resp.raise_for_status()
    current = resp.json()

    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(current, indent=2, ensure_ascii=False))
    print(f"    Snapshot saved → {SNAPSHOT_PATH}")
    print(f"    Current status: {current.get('status')}")
    print(f"    Current title:  {current.get('title', {}).get('raw', '')}")

    # Step 2: Publish new content
    print(f"\n[2/4] Publishing new Privacy Policy HTML...")
    payload = {
        "content": PRIVACY_POLICY_HTML,
        "status": "publish",
        "title": "Privacy Policy",
    }
    put_resp = requests.post(
        f"{api_base}/pages/{PAGE_ID}",
        auth=AUTH,
        json=payload,
        timeout=30,
    )

    if put_resp.status_code not in (200, 201):
        print(f"    ERROR: HTTP {put_resp.status_code}")
        print(put_resp.text[:500])
        sys.exit(1)

    updated = put_resp.json()

    # Step 3: Verify
    print(f"\n[3/4] Verifying...")
    verify_resp = requests.get(
        f"{api_base}/pages/{PAGE_ID}",
        params={"context": "edit"},
        auth=AUTH,
        timeout=30,
    )
    verify_resp.raise_for_status()
    verified = verify_resp.json()

    # Step 4: Report
    print(f"\n[4/4] Summary")
    print(f"    Page ID:     {verified['id']}")
    print(f"    Slug:        {verified['slug']}")
    print(f"    Status:      {verified['status']}")
    print(f"    Title:       {verified['title']['rendered']}")
    print(f"    URL:         {verified['link']}")
    content_len = len(verified.get("content", {}).get("rendered", ""))
    print(f"    Content len: {content_len} chars")

    if verified["status"] == "publish":
        print("\n    SUCCESS — Privacy Policy is live.")
    else:
        print(f"\n    WARNING — Page status is '{verified['status']}', expected 'publish'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
