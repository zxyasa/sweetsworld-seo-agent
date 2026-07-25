# Plan — Mother's Day 2026 Brevo Campaign

**Channel**: Brevo (list_id 5 = direct customers, 3,791 → ~3,100 after suppressions)
**Window**: 2026-04-30 → 2026-05-10 (Mother's Day AU)
**Floor target**: 6-10 attributed orders × $60 AOV = $360-$600

## 3-Email Series

| # | Send (AEST) | Theme | Subject | Audience |
|---|------------|-------|---------|----------|
| 1 | Wed 2026-04-30 10:00 | Plan-ahead | "Sorted for Mum's Day? Here's the easy button 🍫" | Whole list 5 (suppressed) |
| 2 | Mon 2026-05-05 10:00 | Last ship | "Mother's Day shipping closes soon — a heads up" | Non-openers of #1 + new subs |
| 3 | Fri 2026-05-08 10:00 | Last-minute / gift card | "Forgot Mother's Day? We've got a plan." | Non-purchasers |

## Email Copy Drafts

### Email 1 (200 words)
- From: SweetsWorld <hello@sweetsworld.com.au>
- Preheader: Australia-wide delivery, free over $80. Order by May 5 for stress-free arrival.
- Body opening: "Hi {{ contact.FIRSTNAME | default: 'there' }}, Mother's Day is Sunday 10 May — ten sleeps away. If your Mum's the kind who pretends she doesn't want a fuss but absolutely wants a fuss, we've got you."
- CTA: Shop Mother's Day → /product-category/mothers-day-2/
- Signoff: "She doesn't really want another candle. Trust us."

### Email 2 (200 words)
- Preheader: Order today for delivery by Sunday. Australia-wide, free over $80.
- Body opening: "Quick one: if you want a Mother's Day gift delivered before Sunday, today's the day to hit order."
- 3 quick picks: Chocolate Gift Box / The Hamper / Darrell Lea Licorice Bundle

### Email 3 (220 words)
- Preheader: Digital gift cards delivered instantly, plus our ready-to-ship favourites.
- Two options:
  - Option 1: Digital Gift Card → /product/gift-card/ (VERIFY URL EXISTS)
  - Option 2: Express post if order by 2pm Friday
- 3 highest-rated picks listed

## Suppressions
1. bounced
2. unsubscribed
3. last 30d purchasers
4. proxy aliases (BigW/Kogan/eBay/edm — Snippet 32 should already flag)
5. test addresses

→ projected ~18% suppression, net ~3,100 deliverable

## UTM Tagging
`utm_source=brevo&utm_medium=email&utm_campaign=mothers-day-2026&utm_content=email{1|2|3}-{slug}`

## Decisions Baked In
- ❌ NO new coupon code (don't dilute SWEET10, protect AOV/margin, free shipping >$80 IS the discount)
- ✅ Brevo Starter upgrade ($12 AUD/mo) MANDATORY — free 300/day cap blocks 3,100 blast
- ❌ list_id 7 (platform/proxy customers) fully excluded
- ❌ NO new landing page — use existing /product-category/mothers-day-2/ (already has Google Ads sitelink pointing here)
- ❌ NO image hotlinking from sweetsworld.com.au (WebP conversion breaks Outlook/iOS) — use Brevo media or Klaviyo CDN
- ❌ NO "kids" language anywhere (spam-filter flag, also matches Google Ads policy concern)

## Brand Voice
- Aussie, slightly cheeky. Second person ("you", "your Mum"). AU spelling ("favourite", "Mum", "colour")
- Avoid "for kids", all-caps, exclamation stacks
- Free shipping >$80 USP in every email

## Tracking
- Brevo native: opens / clicks / bounces / unsubs
- GA4 (AU-filtered): exploration by source=brevo, campaign=mothers-day-2026, broken by content
- WC UTM attribution: cross-check vs GA4

## Send Approval Workflow
1. Build draft → Brevo
2. Test send → Michael Gmail + secondary inbox
3. Michael QA (subject/preheader/CTA UTM/FIRSTNAME fallback/footer/no-kids)
4. Schedule via Brevo (UTC: 10:00 AEST = 00:00 UTC after AEDT ends April)
5. Monitor first 2h post-send (bounce <3%, unsub <0.5%/hr → ok; else pause)

## Post-Campaign Report (2026-05-13)
- Open / CTR / unsub delta
- GA4 AU revenue attribution per email
- Best-performing subject line → bank for Father's Day (Sep 7)

## Risk Register
- "Kids" word in copy → spam flag (DONE: avoided in drafts)
- FIRSTNAME merge tag empty → liquid fallback `| default: "there"` (DONE: in drafts)
- WebP image breakage → use Brevo media / Klaviyo CDN (DONE)
- Free-tier cap blocks send → upgrade Starter (DONE: in plan)
- Recent purchasers annoyed → exclude last-30d (DONE: in suppression)
- Gift card URL doesn't exist → verify before Step 4; fallback to single-CTA framing
- AEST/UTC confusion → double-check Brevo dashboard preview

(Full plan including verbatim email body HTML in conversation transcript 2026-04-18)
