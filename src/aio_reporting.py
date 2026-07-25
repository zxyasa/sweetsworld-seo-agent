"""Transparent reporting for append-only AIO probe observations."""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Iterable


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def _rate(successes: int, total: int) -> dict[str, Any]:
    low, high = wilson_interval(successes, total)
    return {
        "successes": successes,
        "total": total,
        "rate": successes / total if total else 0.0,
        "ci95_low": low,
        "ci95_high": high,
    }


def _surface_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if not row.get("error_code")]
    positions = [row["recommendation_position"] for row in valid if row.get("recommendation_position")]
    prompt_ids = {row["prompt_id"] for row in valid}
    cited_prompt_ids = {row["prompt_id"] for row in valid if row.get("domain_cited")}
    competitor_counts = Counter(
        competitor for row in valid for competitor in (row.get("competitors") or [])
    )
    competitor_mentions = sum(competitor_counts.values())
    brand_mentions = sum(int(bool(row.get("brand_mentioned"))) for row in valid)
    brand_recommendations = sum(int(bool(row.get("brand_recommended"))) for row in valid)
    all_mentions = brand_mentions + competitor_mentions
    share_of_voice = {"Sweetsworld": brand_mentions / all_mentions if all_mentions else 0.0}
    share_of_voice.update({
        name: count / all_mentions if all_mentions else 0.0
        for name, count in sorted(competitor_counts.items())
    })
    return {
        "observations": len(rows),
        "valid_observations": len(valid),
        "errors": len(rows) - len(valid),
        "brand_mention": _rate(brand_mentions, len(valid)),
        "brand_recommendation": _rate(brand_recommendations, len(valid)),
        "domain_citation": _rate(sum(int(bool(row.get("domain_cited"))) for row in valid), len(valid)),
        "product_citation": _rate(sum(int(bool(row.get("product_cited"))) for row in valid), len(valid)),
        "query_domain_coverage": _rate(len(cited_prompt_ids), len(prompt_ids)),
        "mean_recommendation_position": sum(positions) / len(positions) if positions else None,
        "mention_share_of_voice": share_of_voice,
        "competitor_mentions": competitor_mentions,
    }


def build_run_report(
    run: dict[str, Any],
    rows: Iterable[dict[str, Any]],
    basket_size: int | None = None,
    prior_run: dict[str, Any] | None = None,
    prior_rows: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    materialized = list(rows)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in materialized:
        grouped[(row["provider"], row["surface"])].append(row)
    surfaces = {
        f"{provider}/{surface}": _surface_metrics(group_rows)
        for (provider, surface), group_rows in sorted(grouped.items())
    }
    prompt_ids = {row["prompt_id"] for row in materialized}
    report = {
        "run": run,
        "methodology": {
            "unit": "one provider response to one prompt replicate",
            "surface_separation": True,
            "recommendation_detection": "conservative deterministic text-window heuristic",
            "confidence_interval": "Wilson score interval, 95%",
            "important_limit": "API search surfaces are not the ChatGPT UI or Google AI Overviews",
        },
        "basket": {"observed_prompts": len(prompt_ids), "configured_prompts": basket_size},
        "surfaces": surfaces,
    }
    if prior_run is not None and prior_rows is not None:
        prior_materialized = list(prior_rows)
        prior_grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in prior_materialized:
            prior_grouped[(row["provider"], row["surface"])].append(row)
        prior_surfaces = {
            f"{provider}/{surface}": _surface_metrics(group_rows)
            for (provider, surface), group_rows in sorted(prior_grouped.items())
        }
        deltas: dict[str, Any] = {}
        for label, metrics in surfaces.items():
            if label not in prior_surfaces:
                continue
            before = prior_surfaces[label]
            deltas[label] = {
                key: metrics[key]["rate"] - before[key]["rate"]
                for key in ("brand_mention", "brand_recommendation", "domain_citation", "product_citation")
            }
        report["comparison"] = {
            "prior_run_id": prior_run["run_id"],
            "rate_deltas": deltas,
        }
    else:
        report["comparison"] = None
    return report


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def render_markdown(report: dict[str, Any]) -> str:
    run = report["run"]
    lines = [
        "# Sweetsworld AIO visibility report",
        "",
        f"- Run: `{run['run_id']}`",
        f"- Status: **{run['status']}**",
        f"- Basket: `{run['basket_version']}`",
        f"- Started: {run['started_at']}",
        f"- Prompt coverage: {report['basket']['observed_prompts']}/{report['basket']['configured_prompts'] or 'unknown'}",
        "",
        "| Measured API surface | Valid | Errors | Brand mention | Recommendation | Domain citation | Product citation | Query citation coverage | Brand mention SOV | Mean position |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, metrics in report["surfaces"].items():
        lines.append(
            "| " + " | ".join([
                label,
                str(metrics["valid_observations"]),
                str(metrics["errors"]),
                _pct(metrics["brand_mention"]["rate"]),
                _pct(metrics["brand_recommendation"]["rate"]),
                _pct(metrics["domain_citation"]["rate"]),
                _pct(metrics["product_citation"]["rate"]),
                _pct(metrics["query_domain_coverage"]["rate"]),
                _pct(metrics["mention_share_of_voice"].get("Sweetsworld")),
                "n/a" if metrics["mean_recommendation_position"] is None else f"{metrics['mean_recommendation_position']:.2f}",
            ]) + " |"
        )
    comparison = report.get("comparison")
    if comparison and comparison["rate_deltas"]:
        lines += ["", f"## Change from `{comparison['prior_run_id']}`", ""]
        for label, deltas in comparison["rate_deltas"].items():
            lines.append(
                f"- {label}: mention {deltas['brand_mention'] * 100:+.1f} pp; "
                f"recommendation {deltas['brand_recommendation'] * 100:+.1f} pp; "
                f"domain citation {deltas['domain_citation'] * 100:+.1f} pp"
            )
    lines += [
        "",
        "## Method limits",
        "",
        "OpenAI Responses web search and Gemini grounded search are measured separately. These results are not ChatGPT UI or Google AI Overviews measurements. Recommendation detection is a reviewable heuristic; raw provider responses are retained for audit.",
        "",
        "Rates should be read with their stored numerator, denominator and 95% Wilson interval, especially while the sample is small.",
    ]
    return "\n".join(lines) + "\n"


def format_telegram(report: dict[str, Any]) -> str:
    run = report["run"]
    lines = [f"Sweetsworld AIO — {run['status']}", f"Basket: {run['basket_version']}"]
    for label, metrics in report["surfaces"].items():
        lines += [
            "",
            label,
            f"Valid/errors: {metrics['valid_observations']}/{metrics['errors']}",
            f"Mention {_pct(metrics['brand_mention']['rate'])} · Recommend {_pct(metrics['brand_recommendation']['rate'])}",
            f"Domain citation {_pct(metrics['domain_citation']['rate'])} · Product {_pct(metrics['product_citation']['rate'])}",
            f"Brand mention SOV {_pct(metrics['mention_share_of_voice'].get('Sweetsworld'))}",
        ]
    comparison = report.get("comparison")
    if comparison and comparison["rate_deltas"]:
        lines += ["", f"Vs {comparison['prior_run_id'][:8]}:"]
        for label, deltas in comparison["rate_deltas"].items():
            lines.append(
                f"{label}: mention {deltas['brand_mention'] * 100:+.1f}pp · citation {deltas['domain_citation'] * 100:+.1f}pp"
            )
    lines += ["", "Note: API search measurements, not ChatGPT UI / Google AI Overviews."]
    return "\n".join(lines)
