# Pilot QA Notes

Last updated: 2026-03-16T04:41:10Z

## Reviewed Samples
- `white-knight-chocolate-where-to-buy-australia`
- `fantales-lollies-buying-guide`
- `are-jolly-ranchers-halal`

## Issues Found And Fixed
- `where to buy` queries were initially misclassified as `category_page`; they now export as `landing_page` when the buying signal is in the primary keyword.
- Guide-style titles were initially too easy to misclassify as landing pages; `Buying Guide` style titles now resolve to `guide_page` unless the primary keyword itself is explicitly transactional.
- Guide copy initially repeated raw query strings like `are jolly ranchers halal`; the brief engine now rewrites those into more natural phrases such as `whether jolly ranchers are halal`.
- Product matching originally could not be tested because there was no `data/products.json`; a real catalog has now been synced from the public WooCommerce Store API.
- Deterministic matching initially over-weighted generic words like `lollies`; the selector now drops those generic fallbacks so it does not invent relevance when the exact brand/product is missing.

## Current Sample Outcomes
- white-knight-chocolate-where-to-buy-australia
  - Correctly classified as landing_page.
  - Real product block now renders with 1 exact phrase-matched product: White Knights Chocolate Mint Chews- 120g.
- antales-lollies-buying-guide
  - Correctly classified as guide_page.
  - Now exports with 3 explicit fallback products so the page can cover both smaller and larger pack intent:
    Milk Chocolate Chewy Caramel 1.8kg, Milk Chocolate Chewy Caramel 6kg, and Milk Chocolate Chewy Caramel 150g.
- re-jolly-ranchers-halal
  - Correctly classified as guide_page.
  - Now exports with 4 matched Jolly Rancher products.

## Remaining Risks
- Link target selection is still generic fallback quality; Step 9 should improve which pages are linked, not just the anchor text.
- Fantales still relies on an explicit substitute-product fallback because there is no exact Fantales SKU in the synced catalog.
- Sample pages are stronger than the original template, but they still need human approval before any page can move to pproved or published.

## QA Direction For The Next Pass
- Review the three current sample packs and confirm whether the current product substitutions are acceptable for pilot approval.
- Tighten internal-link targets before approving any batch for publication.
- Only move samples toward pproved after a human review of page.html, the brief JSON, the checklist, and the matched product list.
