from aio_reporting import build_run_report, format_telegram, render_markdown, wilson_interval


def _row(**changes):
    row = {
        "provider": "openai", "surface": "responses_web_search_api", "prompt_id": "q1",
        "error_code": "", "brand_mentioned": 1, "brand_recommended": 1,
        "domain_cited": 1, "product_cited": 1, "recommendation_position": 2,
        "competitors": ["Lolly Mart"],
    }
    row.update(changes)
    return row


def test_wilson_interval_contains_observed_rate():
    low, high = wilson_interval(4, 10)
    assert low < 0.4 < high


def test_report_keeps_provider_surfaces_separate_and_excludes_errors():
    run = {"run_id": "run-1", "status": "partial", "basket_version": "v1", "started_at": "now"}
    rows = [
        _row(),
        _row(prompt_id="q2", error_code="429", brand_mentioned=0),
        _row(provider="google", surface="gemini_grounding_api", prompt_id="q1", domain_cited=0),
    ]
    report = build_run_report(run, rows, 30)
    openai = report["surfaces"]["openai/responses_web_search_api"]
    google = report["surfaces"]["google/gemini_grounding_api"]
    assert openai["valid_observations"] == 1
    assert openai["errors"] == 1
    assert openai["domain_citation"]["rate"] == 1.0
    assert google["domain_citation"]["rate"] == 0.0
    assert openai["mention_share_of_voice"] == {"Sweetsworld": 0.5, "Lolly Mart": 0.5}


def test_report_calculates_rate_deltas_against_prior_run():
    current = {"run_id": "current", "status": "completed", "basket_version": "v2", "started_at": "now"}
    prior = {"run_id": "prior", "status": "completed", "basket_version": "v1", "started_at": "before"}
    report = build_run_report(
        current,
        [_row(domain_cited=1)],
        30,
        prior,
        [_row(domain_cited=0)],
    )
    delta = report["comparison"]["rate_deltas"]["openai/responses_web_search_api"]
    assert delta["domain_citation"] == 1.0


def test_renderers_disclose_surface_limit():
    run = {"run_id": "run-1", "status": "completed", "basket_version": "v1", "started_at": "now"}
    report = build_run_report(run, [_row()], 30)
    assert "not ChatGPT UI" in render_markdown(report)
    assert "not ChatGPT UI" in format_telegram(report)
