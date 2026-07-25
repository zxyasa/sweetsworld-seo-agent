"""GTM: add 3 missing GA4 ecommerce event tags + triggers.

Adds to GTM-TCKSG2Z workspace 21:
  - Custom Event triggers: view_cart / add_shipping_info / add_payment_info
  - GA4 Event tags firing on those, with currency + value + items + coupon params

Mirrors existing GA4 - Begin Checkout (tag 41) config exactly.
Does NOT publish — leaves changes in workspace for preview/test, then user clicks Publish in UI
(or run gtm_publish_workspace.py).

Run:
    .venv/bin/python scripts/gtm_add_ecommerce_events.py
"""
from __future__ import annotations

import json
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/tagmanager.edit.containers"]
ACCT = "6000822737"
CONT = "30948774"
WS = "21"
WS_PATH = f"accounts/{ACCT}/containers/{CONT}/workspaces/{WS}"

EVENTS = ["view_cart", "add_shipping_info", "add_payment_info"]

# ecommerce param block — copied from tag 41 (Begin Checkout)
EVENT_SETTINGS_TABLE = [
    {
        "type": "map",
        "map": [
            {"type": "template", "key": "parameter", "value": "currency"},
            {"type": "template", "key": "parameterValue", "value": "{{DLV - ecommerce.currency}}"},
        ],
    },
    {
        "type": "map",
        "map": [
            {"type": "template", "key": "parameter", "value": "value"},
            {"type": "template", "key": "parameterValue", "value": "{{DLV - ecommerce.value}}"},
        ],
    },
    {
        "type": "map",
        "map": [
            {"type": "template", "key": "parameter", "value": "items"},
            {"type": "template", "key": "parameterValue", "value": "{{DLV - ecommerce.items}}"},
        ],
    },
    {
        "type": "map",
        "map": [
            {"type": "template", "key": "parameter", "value": "coupon"},
            {"type": "template", "key": "parameterValue", "value": "{{DLV - ecommerce.coupon}}"},
        ],
    },
]
MEASUREMENT_ID = "G-J17HXZSL3P"


def main() -> int:
    creds = service_account.Credentials.from_service_account_file(
        "gsc_credentials.json", scopes=SCOPES
    )
    svc = build("tagmanager", "v2", credentials=creds, cache_discovery=False)
    tags_api = svc.accounts().containers().workspaces().tags()
    trig_api = svc.accounts().containers().workspaces().triggers()

    # idempotency: list existing tags + triggers, skip if name match
    existing_tags = {t["name"]: t["tagId"] for t in tags_api.list(parent=WS_PATH).execute().get("tag", [])}
    existing_trigs = {t["name"]: t["triggerId"] for t in trig_api.list(parent=WS_PATH).execute().get("trigger", [])}

    print("=== Adding GA4 ecommerce events to GTM-TCKSG2Z workspace 21 ===\n")
    summary = []

    for ev in EVENTS:
        trig_name = f"Custom Event - {ev}"
        tag_name = f"GA4 - {ev.replace('_', ' ').title()}"

        # 1. trigger
        if trig_name in existing_trigs:
            trig_id = existing_trigs[trig_name]
            print(f"  trigger '{trig_name}' already exists (id={trig_id}) — skip create")
        else:
            trig_body = {
                "name": trig_name,
                "type": "customEvent",
                "customEventFilter": [
                    {
                        "type": "equals",
                        "parameter": [
                            {"type": "template", "key": "arg0", "value": "{{_event}}"},
                            {"type": "template", "key": "arg1", "value": ev},
                        ],
                    }
                ],
            }
            r = trig_api.create(parent=WS_PATH, body=trig_body).execute()
            trig_id = r["triggerId"]
            print(f"  + trigger created '{trig_name}' id={trig_id}")

        # 2. tag
        if tag_name in existing_tags:
            tag_id = existing_tags[tag_name]
            print(f"  tag '{tag_name}' already exists (id={tag_id}) — skip create")
        else:
            tag_body = {
                "name": tag_name,
                "type": "gaawe",
                "parameter": [
                    {"type": "boolean", "key": "sendEcommerceData", "value": "true"},
                    {"type": "list", "key": "eventSettingsTable", "list": EVENT_SETTINGS_TABLE},
                    {"type": "template", "key": "eventName", "value": ev},
                    {"type": "template", "key": "measurementIdOverride", "value": MEASUREMENT_ID},
                ],
                "firingTriggerId": [trig_id],
                "consentSettings": {"consentStatus": "notSet"},
            }
            r = tags_api.create(parent=WS_PATH, body=tag_body).execute()
            tag_id = r["tagId"]
            print(f"  + tag created     '{tag_name}' id={tag_id} fires on trig {trig_id}")

        summary.append({"event": ev, "trigger_id": trig_id, "tag_id": tag_id, "tag_name": tag_name})

    print()
    print("=== Done ===")
    print(json.dumps(summary, indent=2))
    print()
    print("Next steps:")
    print(f"  1. Preview: https://tagmanager.google.com/#/container/accounts/{ACCT}/containers/{CONT}/workspaces/{WS}")
    print("     Click 'Preview' → walk through Cart / Shipping / Payment pages → confirm 3 tags fire")
    print("  2. Publish: 'Submit' button (or run gtm_publish_workspace.py once we wire it)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
