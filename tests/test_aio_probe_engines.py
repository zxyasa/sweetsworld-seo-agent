from aio_probe_engines import analyse_evidence, parse_gemini_response, parse_openai_response


def test_parse_openai_response_labels_surface_and_collects_sources():
    payload = {
        "model": "gpt-test-2026-01-01",
        "output": [
            {"type": "web_search_call", "action": {"sources": [{"url": "https://example.com/a"}]}},
            {"type": "message", "content": [{
                "type": "output_text",
                "text": "Try Sweetsworld.",
                "annotations": [{"type": "url_citation", "url": "https://sweetsworld.com.au/candy/test"}],
            }]},
        ],
        "usage": {"input_tokens": 12, "output_tokens": 8},
    }
    result = parse_openai_response(payload, 123)
    assert result.surface == "responses_web_search_api"
    assert result.answer_text == "Try Sweetsworld."
    assert result.citation_urls == ["https://sweetsworld.com.au/candy/test"]
    assert result.source_urls == ["https://example.com/a", "https://sweetsworld.com.au/candy/test"]
    assert (result.input_tokens, result.output_tokens, result.latency_ms) == (12, 8, 123)


def test_parse_gemini_response_collects_grounding_metadata():
    payload = {
        "modelVersion": "gemini-test-001",
        "candidates": [{
            "content": {"parts": [{"text": "One"}, {"text": "Two"}]},
            "groundingMetadata": {"groundingChunks": [
                {"web": {"uri": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/abc", "title": "sweetsworld.com.au"}}
            ]},
        }],
        "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 3},
    }
    result = parse_gemini_response(payload, "gemini-test", 99)
    assert result.surface == "gemini_grounding_api"
    assert result.model_version == "gemini-test-001"
    assert result.answer_text == "One\nTwo"
    assert result.citation_urls == ["https://vertexaisearch.cloud.google.com/grounding-api-redirect/abc"]
    assert result.source_urls == [
        "https://vertexaisearch.cloud.google.com/grounding-api-redirect/abc",
        "https://sweetsworld.com.au/",
    ]


def test_analyse_evidence_is_domain_safe_and_ranks_mentions():
    evidence = analyse_evidence(
        "Lolly Mart is common. I recommend Sweets World as another online shop.",
        ["https://shop.sweetsworld.com.au/candy/abc", "https://notsweetsworld.com.au/"],
        [],
        ["Sweetsworld", "Sweets World"],
        "sweetsworld.com.au",
        [{"name": "Lolly Mart", "aliases": ["LollyMart"]}],
    )
    assert evidence == {
        "brand_mentioned": True,
        "brand_recommended": True,
        "domain_cited": True,
        "product_cited": True,
        "recommendation_position": 2,
        "competitors": ["Lolly Mart"],
    }


def test_analyse_evidence_does_not_treat_bare_mention_as_recommendation():
    evidence = analyse_evidence(
        "A historical list included Sweetsworld in 2019.", [], [], ["Sweetsworld"],
        "sweetsworld.com.au", [],
    )
    assert evidence["brand_mentioned"] is True
    assert evidence["brand_recommended"] is False
    assert evidence["recommendation_position"] is None
