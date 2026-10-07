from api.agents.router import route_none


def test_denied_domain_names_the_agent():
    state = {"allowed_domains": {"hr_rag"}, "denied_domain": "github"}
    result = route_none(state)
    assert "GitHub (coroot)" in result["answer"]
    assert "contact an admin" in result["answer"]


def test_no_allowed_domains_at_all():
    state = {"allowed_domains": set()}
    result = route_none(state)
    assert "no agent access configured" in result["answer"]


def test_ambiguous_classification():
    state = {"allowed_domains": {"hr_rag", "sales_sql"}}
    result = route_none(state)
    assert "couldn't confidently match" in result["answer"].lower()
