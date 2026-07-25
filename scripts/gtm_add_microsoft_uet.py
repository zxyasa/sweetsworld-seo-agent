"""Add Microsoft Advertising UET (base + purchase conversion) to GTM-TCKSG2Z.
Reuses the gsc_credentials.json service account already authorized to edit the
container. Idempotent: skips tags that already exist. Leaves changes in the
workspace (does NOT publish) — review + Submit in the GTM UI, or run publish.
"""
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/tagmanager.edit.containers"]
ACCT, CONT, WS = "6000822737", "30948774", "22"
UET_TAG_ID = "283013249"
PURCHASE_TRIGGER_ID = "36"  # Custom Event - purchase

BASE = f"accounts/{ACCT}/containers/{CONT}/workspaces/{WS}"


def main():
    creds = service_account.Credentials.from_service_account_file(
        "gsc_credentials.json", scopes=SCOPES
    )
    svc = build("tagmanager", "v2", credentials=creds, cache_discovery=False)
    tags_api = svc.accounts().containers().workspaces().tags()

    existing = {t["name"]: t for t in tags_api.list(parent=BASE).execute().get("tag", [])}

    # The community Microsoft UET template is fiddly to reference by id; use a
    # Custom HTML tag with the official UET snippet — same result, no template
    # dependency. Base loads the library on all pages.
    base_html = (
        '<script>(function(w,d,t,r,u){var f,n,i;w[u]=w[u]||[],f=function(){'
        'var o={ti:"' + UET_TAG_ID + '",enableAutoSpa:true};o.q=w[u],w[u]=new UET(o),w[u].push("pageLoad")},'
        'n=d.createElement(t),n.src=r,n.async=1,n.onload=n.onreadystatechange=function(){'
        'var s=this.readyState;s&&s!=="loaded"&&s!=="complete"||(f(),n.onload=n.onreadystatechange=null)},'
        'i=d.getElementsByTagName(t)[0],i.parentNode.insertBefore(n,i)})'
        '(window,document,"script","//bat.bing.com/bat.js","uetq");</script>'
    )
    base_tag = {
        "name": "Microsoft UET - Base",
        "type": "html",
        "parameter": [
            {"type": "template", "key": "html", "value": base_html},
            {"type": "boolean", "key": "supportDocumentWrite", "value": "false"},
        ],
        "firingTriggerId": ["2147479553"],  # All Pages
    }

    # Purchase conversion: report revenue + currency on the purchase event.
    conv_html = (
        '<script>window.uetq=window.uetq||[];'
        'window.uetq.push("event","purchase",{'
        '"revenue_value":{{DLV - ecommerce.value}},'
        '"currency":"{{DLV - ecommerce.currency}}"});</script>'
    )
    conv_tag = {
        "name": "Microsoft UET - Purchase",
        "type": "html",
        "parameter": [
            {"type": "template", "key": "html", "value": conv_html},
            {"type": "boolean", "key": "supportDocumentWrite", "value": "false"},
        ],
        "firingTriggerId": [PURCHASE_TRIGGER_ID],
        "tagFiringOption": "oncePerEvent",
    }

    for tag in (base_tag, conv_tag):
        if tag["name"] in existing:
            print(f"  ⏭  已存在,跳过: {tag['name']}")
            continue
        created = tags_api.create(parent=BASE, body=tag).execute()
        print(f"  ✅ 已创建: {created['name']} (tagId={created['tagId']})")

    print(f"\n预览: https://tagmanager.google.com/#/container/accounts/{ACCT}/containers/{CONT}/workspaces/{WS}")
    print("发布: GTM UI 点 Submit(或跑 publish 脚本)")


if __name__ == "__main__":
    main()
