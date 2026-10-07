from unittest.mock import MagicMock, patch

from api.agents.router import _keyword_domain, classify


def test_order_question_matches_sales():
    assert _keyword_domain("How many orders are there in total?") == "sales_sql"


def test_commit_question_matches_github():
    assert _keyword_domain("Any recent commits to the repo?") == "github"


def test_pto_question_matches_hr():
    assert _keyword_domain("What's the PTO policy?") == "hr_rag"


def test_no_match_returns_none():
    assert _keyword_domain("What do you think about this?") is None


def test_out_of_scope_keyword_denies_without_calling_llm():
    state = {
        "allowed_domains": {"hr_rag", "sales_sql"},
        "message": "Any recent commits to the repo?",
    }
    result = classify(state)
    assert result["route"] == "none"
    assert result["denied_domain"] == "github"


def test_click_through_rate_question_matches_github():
    question = "Any recent 1 week changes in the code that could explain a 15% drop in click-through rate in a recommendation system?"
    assert _keyword_domain(question) == "github"


def test_code_of_conduct_does_not_false_positive_on_github():
    assert _keyword_domain("What's in the code of conduct?") != "github"


def test_in_scope_keyword_routes_directly():
    state = {
        "allowed_domains": {"hr_rag", "sales_sql"},
        "message": "How many orders are there?",
    }
    result = classify(state)
    assert result["route"] == "sales_sql"


def test_gibberish_question_routes_to_none_via_unsure():
    fake_response = MagicMock()
    fake_response.content = "unsure: question doesn't match any category"
    with patch("api.agents.router.get_llm") as mock_get_llm:
        mock_get_llm.return_value.invoke.return_value = fake_response
        state = {
            "allowed_domains": {"hr_rag", "sales_sql", "github"},
            "message": "fgsfg",
        }
        result = classify(state)
    assert result["route"] == "none"
    assert "denied_domain" not in result


def test_hedged_reason_overrides_forced_category_guess():
    """Small models sometimes still pick a category even when told to say
    'unsure' -- but the reason text itself often hedges anyway."""
    fake_response = MagicMock()
    fake_response.content = "hr_rag: unclear what this question refers to"
    with patch("api.agents.router.get_llm") as mock_get_llm:
        mock_get_llm.return_value.invoke.return_value = fake_response
        state = {
            "allowed_domains": {"hr_rag", "sales_sql", "github"},
            "message": "fgsfg",
        }
        result = classify(state)
    assert result["route"] == "none"
    assert "denied_domain" not in result
