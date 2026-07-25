#!/usr/bin/env python3
"""Run the Sweetsworld AIO query basket without mutating the website.

The command is a dry-run unless ``--live`` is supplied explicitly.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aio_probe_engines import ProbeAPIError, analyse_evidence, query_gemini, query_openai
from aio_scoreboard import AIOScoreboard, ProbeObservation


def load_basket(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"site_id", "version", "brand", "default_location", "competitors", "prompts"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Query basket missing keys: {', '.join(sorted(missing))}")
    prompt_ids = [prompt.get("id") for prompt in data["prompts"]]
    if not prompt_ids or any(not value for value in prompt_ids):
        raise ValueError("Every query basket prompt needs a non-empty id")
    if len(prompt_ids) != len(set(prompt_ids)):
        raise ValueError("Query basket prompt ids must be unique")
    return data


def load_config(site_id: str) -> dict[str, str]:
    values: dict[str, str] = {}
    # Central registry is the shared baseline. Project/site files and the
    # process environment remain valid explicit overrides for compatibility.
    for path in (
        Path.home() / "agents" / ".secrets" / "keys.env",
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / "sites" / site_id / ".env",
    ):
        if path.exists():
            values.update({key: str(value) for key, value in dotenv_values(path).items() if value is not None})
    values.update(os.environ)
    return values


def parse_providers(value: str) -> list[str]:
    aliases = {"gemini": "google", "google": "google", "openai": "openai"}
    providers: list[str] = []
    for item in value.split(","):
        key = item.strip().casefold()
        if key not in aliases:
            raise argparse.ArgumentTypeError(f"Unknown provider: {item}")
        canonical = aliases[key]
        if canonical not in providers:
            providers.append(canonical)
    if not providers:
        raise argparse.ArgumentTypeError("At least one provider is required")
    return providers


def one_per_cluster(prompts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for prompt in prompts:
        cluster = str(prompt["cluster"])
        if cluster not in seen:
            selected.append(prompt)
            seen.add(cluster)
    return selected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only AIO visibility probe")
    parser.add_argument("--site", default="sweetsworld")
    parser.add_argument("--basket", type=Path)
    parser.add_argument("--providers", type=parse_providers, default=parse_providers("openai,google"))
    parser.add_argument("--replicates", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0, help="Limit prompts; 0 uses the full basket")
    parser.add_argument(
        "--one-per-cluster",
        action="store_true",
        help="Select the first prompt from each query cluster before applying --limit",
    )
    parser.add_argument("--live", action="store_true", help="Actually call provider APIs and store evidence")
    parser.add_argument("--trigger", default="manual")
    parser.add_argument("--timeout", type=int, default=90)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.replicates < 1:
        raise SystemExit("--replicates must be at least 1")
    basket_path = args.basket or PROJECT_ROOT / "sites" / args.site / "aio_query_basket.json"
    basket = load_basket(basket_path)
    prompts = basket["prompts"]
    if args.one_per_cluster:
        prompts = one_per_cluster(prompts)
    prompts = prompts[: args.limit or None]
    call_count = len(prompts) * len(args.providers) * args.replicates
    clusters = sorted({prompt["cluster"] for prompt in prompts})
    mode = "LIVE" if args.live else "DRY-RUN"
    print(f"AIO {mode}: site={args.site} basket={basket['version']} prompts={len(prompts)} calls={call_count}")
    print(f"providers={','.join(args.providers)} clusters={','.join(clusters)}")
    if not args.live:
        print("No API requests made; no database rows written. Add --live to execute.")
        return 0

    config = load_config(args.site)
    provider_settings = {
        "openai": {
            "key": config.get("OPENAI_API_KEY", ""),
            "model": config.get("AIO_OPENAI_MODEL", "gpt-5-mini"),
        },
        "google": {
            "key": config.get("GEMINI_API_KEY", "") or config.get("GOOGLE_API_KEY", ""),
            "model": config.get("AIO_GEMINI_MODEL", "gemini-2.5-flash"),
        },
    }
    missing = [provider for provider in args.providers if not provider_settings[provider]["key"]]
    if missing:
        raise SystemExit(f"Missing API key for: {', '.join(missing)}")

    data_dir = PROJECT_ROOT / "sites" / args.site / "data"
    scoreboard = AIOScoreboard(data_dir / "site.db", data_dir / "aio_raw")
    run_id = scoreboard.start_run(args.site, basket["version"], args.trigger)
    successes = 0
    errors = 0
    brand = basket["brand"]
    for prompt in prompts:
        location = {**basket["default_location"], **prompt.get("location", {})}
        for provider in args.providers:
            settings = provider_settings[provider]
            for replicate in range(1, args.replicates + 1):
                try:
                    if provider == "openai":
                        result = query_openai(
                            prompt["query"], settings["key"], settings["model"], location, args.timeout
                        )
                    else:
                        result = query_gemini(
                            prompt["query"], settings["key"], settings["model"], location, args.timeout
                        )
                    evidence = analyse_evidence(
                        result.answer_text,
                        result.citation_urls,
                        result.source_urls,
                        brand["aliases"],
                        brand["domain"],
                        basket["competitors"],
                    )
                    scoreboard.log(
                        ProbeObservation(
                            run_id=run_id,
                            site_id=args.site,
                            prompt_id=prompt["id"],
                            prompt_version=basket["version"],
                            query=prompt["query"],
                            provider=result.provider,
                            surface=result.surface,
                            model=result.model or settings["model"],
                            model_version=result.model_version,
                            location=location,
                            replicate_no=replicate,
                            answer_text=result.answer_text,
                            citation_urls=result.citation_urls,
                            source_urls=result.source_urls,
                            latency_ms=result.latency_ms,
                            input_tokens=result.input_tokens,
                            output_tokens=result.output_tokens,
                            **evidence,
                        ),
                        result.raw_response,
                    )
                    successes += 1
                except ProbeAPIError as exc:
                    errors += 1
                    surface = "responses_web_search_api" if provider == "openai" else "gemini_grounding_api"
                    scoreboard.log(
                        ProbeObservation(
                            run_id=run_id,
                            site_id=args.site,
                            prompt_id=prompt["id"],
                            prompt_version=basket["version"],
                            query=prompt["query"],
                            provider=provider,
                            surface=surface,
                            model=settings["model"],
                            location=location,
                            replicate_no=replicate,
                            error_code=str(exc.status_code),
                            error_message=str(exc)[:1000],
                        ),
                        exc.raw,
                    )
                    print(f"ERROR {provider} {prompt['id']} replicate={replicate}: HTTP {exc.status_code}")
                except Exception as exc:  # preserve the run ledger on transport failures
                    errors += 1
                    surface = "responses_web_search_api" if provider == "openai" else "gemini_grounding_api"
                    scoreboard.log(
                        ProbeObservation(
                            run_id=run_id,
                            site_id=args.site,
                            prompt_id=prompt["id"],
                            prompt_version=basket["version"],
                            query=prompt["query"],
                            provider=provider,
                            surface=surface,
                            model=settings["model"],
                            location=location,
                            replicate_no=replicate,
                            error_code=type(exc).__name__,
                            error_message=str(exc)[:1000],
                        )
                    )
                    print(f"ERROR {provider} {prompt['id']} replicate={replicate}: {type(exc).__name__}")
    status = "completed" if not errors else ("partial" if successes else "failed")
    scoreboard.finish_run(run_id, status, f"successes={successes}; errors={errors}")
    print(f"run_id={run_id} status={status} successes={successes} errors={errors}")
    return 0 if status != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
