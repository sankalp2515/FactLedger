import pytest
from product_core.investigation.search import plan_queries


def test_queries_use_human_month_and_approval_opposition():
    queries = plan_queries([{"id": "c", "subject": "Solar Grant", "period": "2024-02", "stage": "APPROVED"}])
    assert all("February 2024" in q["query"] for q in queries)
    opposing = next(q["query"] for q in queries if q["purpose"] == "OPPOSING")
    assert "rejected" in opposing and "cancelled" in opposing
    assert "delay problems" not in opposing


def test_later_round_queries_target_gaps_without_internal_round_label():
    queries = plan_queries(
        [{"id": "c", "subject": "Solar Grant", "stage": "UNKNOWN", "measure": "EXPENDED"}],
        [{"claim_id": "c", "type": "MISSING_COMPARABLE_EVIDENCE"}],
        2,
    )
    assert "round 2" not in queries[0]["query"]
    assert "missing_comparable_evidence" not in queries[0]["query"]


def _select(claims, batches):
    from product_core.investigation.selection import select_discovery

    return select_discovery(claims, batches)


def test_canonical_identity_preserves_distinct_hosts_and_ordered_repeated_parameters():
    urls = [
        "https://records.example/record?id=1&id=2",
        "https://records.example/record?id=2&id=1",
        "https://www.records.example/record?id=1&id=2",
    ]
    selected = _select(
        [{"id": "c", "subject": "River Bridge"}],
        [
            {
                "claim_id": "c",
                "purpose": "PRIMARY_RECORD",
                "results": [{"url": url} for url in urls],
            }
        ],
    )
    assert {row["url"] for row in selected} == set(urls)


def test_canonical_tracking_removal_preserves_nontracking_encoding_and_default_port_identity():
    from product_core.investigation.selection import canonical_url

    assert canonical_url("https://records.example:443/a?path=%2f&id=1&utm_source=x&id=2#anchor") == (
        "https://records.example/a?path=%2f&id=1&id=2"
    )


def test_primary_query_retains_assertion_actor_and_confirmed_subject():
    from product_core.schemas import Claim

    claim = Claim(
        id="c",
        text="The Regional Board approved the River Bridge in February 2024.",
        subject="River Bridge",
        geography="Kerala",
        period="2024-02",
        stage="APPROVED",
    ).model_dump()
    primary = next(q["query"] for q in plan_queries([claim]) if q["purpose"] == "PRIMARY_RECORD")
    assert "Regional Board" in primary
    assert "River Bridge" in primary
    assert "February 2024" in primary
    assert "Kerala" in primary


def test_primary_query_deduplicates_keywords_without_losing_actor_or_number():
    claim = {
        "id": "c",
        "subject": "Solar Grant",
        "geography": "India",
        "period": "2024-02",
        "stage": "APPROVED",
        "text": "The Union Cabinet approved Solar Grant for 7.5 million homes in February 2024.",
    }
    primary = next(q["query"] for q in plan_queries([claim]) if q["purpose"] == "PRIMARY_RECORD")
    assert primary.casefold().count("approved") == 1
    assert primary.count("February") == 1 and primary.count("2024") == 1
    assert primary.count("Solar Grant") == 1
    assert "Union Cabinet" in primary and "7.5" in primary


@pytest.mark.parametrize(
    "assertion,geography,scoped",
    [
        ("The Union Cabinet approved Solar Grant.", "India", True),
        ("The Ministry of Energy approved Solar Grant.", "India", True),
        ("Parliament approved Solar Grant.", "India", True),
        ("Acme Solar approved Solar Grant.", "India", False),
        ("Acme cabinet company approved Solar Grant.", "India", False),
        ("The Union Cabinet approved Solar Grant.", "Other country", False),
    ],
)
def test_public_institution_discovery_scope_is_conditional_and_followup_is_unrestricted(
    assertion, geography, scoped
):
    claim = {
        "id": "c",
        "subject": "Solar Grant",
        "geography": geography,
        "period": "2024-02",
        "stage": "APPROVED",
        "text": assertion,
    }
    queries = plan_queries([claim])
    primary = next(q["query"] for q in queries if q["purpose"] == "PRIMARY_RECORD")
    assert ("(site:gov.in OR site:nic.in)" in primary) is scoped
    assert all("site:" not in q["query"] for q in queries if q["purpose"] == "OPPOSING")
    assert "site:" not in plan_queries([claim], round_number=2)[0]["query"]


def test_buried_relevant_original_record_and_opposition_get_first_two_slots():
    claim = {"id": "c", "subject": "Solar Grant", "stage": "APPROVED", "geography": "Kerala"}
    weak = [{"url": f"https://news.example/{i}", "title": "Solar Grant application guide"} for i in range(14)]
    official = {"url": "https://energy.gov.in/solar-grant-approval", "title": "Solar Grant approved Kerala"}
    opposition = {
        "url": "https://journal.example/solar-grant",
        "title": "Solar Grant approval cancelled Kerala",
    }
    selected = _select(
        [claim],
        [
            {"claim_id": "c", "purpose": "PRIMARY_RECORD", "results": weak + [official]},
            {"claim_id": "c", "purpose": "OPPOSING", "results": [opposition]},
        ],
    )
    assert [r["url"] for r in selected[:2]] == [official["url"], opposition["url"]]
    assert all("snippet" not in r for r in selected)
    assert selected[0]["selection"]["original_host_signal"] is True


def test_unrelated_government_host_does_not_outweigh_scoped_record():
    selected = _select(
        [{"id": "c", "subject": "River Bridge"}],
        [
            {
                "claim_id": "c",
                "purpose": "PRIMARY_RECORD",
                "results": [
                    {"url": "https://department.gov.in/weather", "title": "Weather forecast"},
                    {"url": "https://records.example/river-bridge", "title": "River Bridge official record"},
                ],
            }
        ],
    )
    assert selected[0]["url"] == "https://records.example/river-bridge"
    assert selected[1]["selection"]["original_host_signal"] is False


def test_selection_deduplicates_tracking_links_preserves_semantic_queries_and_diversity():
    selected = _select(
        [{"id": "c", "subject": "River Bridge"}],
        [
            {
                "claim_id": "c",
                "purpose": "PRIMARY_RECORD",
                "results": [
                    {"url": "https://records.example/river-bridge?id=1&utm_source=search#section"},
                    {"url": "https://records.example/river-bridge?id=1"},
                    {"url": "https://records.example/river-bridge?id=2"},
                    {"url": "https://independent.example/river-bridge"},
                    {"url": "https://user:secret@records.example/river-bridge"},
                ],
            }
        ],
    )
    assert len(selected) == 3
    assert selected[0]["url"].endswith("utm_source=search#section")
    assert selected[1]["url"] == "https://independent.example/river-bridge"
    assert selected[2]["url"].endswith("id=2")
    repeated = _select(
        [{"id": "c", "subject": "River Bridge"}],
        [{"claim_id": "c", "purpose": "PRIMARY_RECORD", "results": [{"url": r["url"]} for r in selected]}],
    )
    assert [r["url"] for r in repeated] == [r["url"] for r in selected]


@pytest.mark.parametrize(
    "stage,terms",
    [
        ("OPERATIONAL", "nonfunctional"),
        ("PHYSICALLY_COMPLETED", "unfinished"),
        ("PROCURED", "tender"),
        ("INAUGURATED", "inauguration"),
        ("UNDER_CONSTRUCTION", "stalled"),
    ],
)
def test_opposition_queries_target_claimed_stage(stage, terms):
    from product_core.schemas import Claim

    claim = Claim(
        id="c",
        text="River Bridge status",
        subject="River Bridge",
        geography="Kerala",
        period="2024-02",
        stage=stage,
    ).model_dump()
    queries = plan_queries([claim])
    assert terms in next(q["query"] for q in queries if q["purpose"] == "OPPOSING")


@pytest.mark.parametrize(
    "measure,terms,cue",
    [
        ("ALLOCATED", "allocation", "allocated"),
        ("SANCTIONED", "sanction", "sanctioned"),
        ("RELEASED", "unreleased", "released"),
        ("EXPENDED", "unspent", "expenditure"),
    ],
)
def test_unknown_stage_uses_confirmed_funding_measure_for_queries_and_selection(measure, terms, cue):
    from product_core.schemas import Claim

    claim = Claim(
        id="c",
        text="River Bridge funding",
        subject="River Bridge",
        geography="Kerala",
        period="2024-02",
        stage="UNKNOWN",
        measure=measure,
    ).model_dump()
    queries = plan_queries([claim])
    assert all(measure.lower() in q["query"] and "unknown" not in q["query"] for q in queries)
    assert terms in next(q["query"] for q in queries if q["purpose"] == "OPPOSING")
    selected = _select(
        [claim],
        [
            {
                "claim_id": "c",
                "purpose": "PRIMARY_RECORD",
                "results": [
                    {"url": "https://records.example/guide", "title": "River Bridge guide"},
                    {"url": "https://records.example/funding", "title": f"River Bridge {cue}"},
                ],
            }
        ],
    )
    assert selected[0]["url"] == "https://records.example/funding"
    assert selected[0]["selection"]["stage_cue"] is True


@pytest.mark.parametrize(
    "stage,cue",
    [
        ("PHYSICALLY_COMPLETED", "completion"),
        ("PROCURED", "procurement"),
        ("INAUGURATED", "inauguration"),
    ],
)
def test_schema_accepted_stage_cues_prioritize_scoped_record(stage, cue):
    from product_core.schemas import Claim

    claim = Claim(
        id="c",
        text="River Bridge status",
        subject="River Bridge",
        geography="Kerala",
        period="2024-02",
        stage=stage,
    ).model_dump()
    selected = _select(
        [claim],
        [
            {
                "claim_id": "c",
                "purpose": "PRIMARY_RECORD",
                "results": [
                    {"url": "https://records.example/guide", "title": "River Bridge guide"},
                    {"url": "https://records.example/status", "title": f"River Bridge {cue}"},
                ],
            }
        ],
    )
    assert selected[0]["url"] == "https://records.example/status"
    assert selected[0]["selection"]["stage_cue"] is True


def test_snippets_do_not_change_selection_and_lookalike_host_is_not_original():
    claim = {"id": "c", "subject": "River Bridge"}
    batches = [
        {
            "claim_id": "c",
            "purpose": "PRIMARY_RECORD",
            "results": [
                {
                    "url": "https://department.gov.in.evil.example/weather",
                    "title": "Weather",
                    "snippet": "River Bridge",
                },
                {"url": "https://records.example/river-bridge", "title": "River Bridge"},
            ],
        }
    ]
    selected = _select([claim], batches)
    assert selected[0]["url"] == "https://records.example/river-bridge"
    assert not selected[1]["selection"]["original_host_signal"]
    batches[0]["results"][0]["snippet"] = "unrelated"
    assert _select([claim], batches) == selected


def test_multiple_claims_each_get_primary_then_opposing_opportunity():
    claims = [{"id": "c1", "subject": "River Bridge"}, {"id": "c2", "subject": "Solar Grant"}]
    batches = [
        {
            "claim_id": claim["id"],
            "purpose": purpose,
            "results": [
                {"url": f"https://records.example/{claim['id']}/{purpose}", "title": claim["subject"]}
            ],
        }
        for purpose in ("PRIMARY_RECORD", "OPPOSING")
        for claim in claims
    ]
    selected = _select(claims, batches)
    assert [(r["selection"]["claim_id"], r["selection"]["purpose"]) for r in selected] == [
        ("c1", "PRIMARY_RECORD"),
        ("c1", "OPPOSING"),
        ("c2", "PRIMARY_RECORD"),
        ("c2", "OPPOSING"),
    ]
