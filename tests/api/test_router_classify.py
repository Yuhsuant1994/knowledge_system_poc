from unittest.mock import MagicMock, patch

from api.agents.router import classify


def _mock_llm_reply(content):
    fake_response = MagicMock()
    fake_response.content = content
    return patch("api.agents.router.get_llm", return_value=MagicMock(invoke=MagicMock(return_value=fake_response)))


def test_out_of_scope_llm_match_denies():
    with _mock_llm_reply("github: mentions commits"):
        state = {
            "allowed_domains": {"hr_rag", "sales_sql"},
            "message": "Any recent commits to the repo?",
        }
        result = classify(state)
    assert result["route"] == "none"
    assert result["denied_domain"] == "github"


def test_in_scope_llm_match_routes_directly():
    with _mock_llm_reply("sales_sql: asks for an order count"):
        state = {
            "allowed_domains": {"hr_rag", "sales_sql"},
            "message": "How many orders are there?",
        }
        result = classify(state)
    assert result["route"] == "sales_sql"


def test_gibberish_question_routes_to_none_via_unsure():
    with _mock_llm_reply("unsure: question doesn't match any category"):
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
    with _mock_llm_reply("hr_rag: unclear what this question refers to"):
        state = {
            "allowed_domains": {"hr_rag", "sales_sql", "github"},
            "message": "fgsfg",
        }
        result = classify(state)
    assert result["route"] == "none"
    assert "denied_domain" not in result
