import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock, patch

import pytest

from api.agents import github_agent


def _settings_with(**overrides):
    return replace(github_agent.settings, **overrides)


@pytest.mark.asyncio
async def test_answer_requires_repo(monkeypatch):
    monkeypatch.setattr(github_agent, "settings", _settings_with(github_repo=""))
    result = await github_agent.answer("anything")
    assert "GITHUB_REPO" in result["answer"]


@pytest.mark.asyncio
async def test_answer_requires_token(monkeypatch):
    monkeypatch.setattr(
        github_agent,
        "settings",
        _settings_with(github_repo="coroot/coroot", github_token=""),
    )
    result = await github_agent.answer("anything")
    assert "GITHUB_PERSONAL_ACCESS_TOKEN" in result["answer"]


@pytest.mark.asyncio
async def test_answer_handles_fetch_timeout(monkeypatch):
    monkeypatch.setattr(
        github_agent,
        "settings",
        _settings_with(github_repo="coroot/coroot", github_token="fake"),
    )
    monkeypatch.setattr(github_agent, "FETCH_TIMEOUT_SECONDS", 0.05)

    async def never_returns():
        await asyncio.sleep(10)

    monkeypatch.setattr(github_agent, "_fetch_recent_commits", never_returns)
    result = await github_agent.answer("any recent commits?")
    assert "took longer than" in result["answer"]
    assert result["sources"] == ["coroot/coroot"]


@pytest.mark.asyncio
async def test_answer_handles_fetch_error(monkeypatch):
    monkeypatch.setattr(
        github_agent,
        "settings",
        _settings_with(github_repo="coroot/coroot", github_token="fake"),
    )

    async def boom():
        raise RuntimeError("list_commits not found")

    monkeypatch.setattr(github_agent, "_fetch_recent_commits", boom)
    result = await github_agent.answer("any recent commits?")
    assert "couldn't fetch commits" in result["answer"].lower()


@pytest.mark.asyncio
async def test_answer_handles_llm_timeout(monkeypatch):
    monkeypatch.setattr(
        github_agent,
        "settings",
        _settings_with(github_repo="coroot/coroot", github_token="fake"),
    )
    monkeypatch.setattr(github_agent, "LLM_TIMEOUT_SECONDS", 0.05)

    async def fake_fetch():
        return "2026-01-01T00:00:00Z", "[]"

    monkeypatch.setattr(github_agent, "_fetch_recent_commits", fake_fetch)

    class SlowLLM:
        async def ainvoke(self, prompt):
            await asyncio.sleep(10)

    monkeypatch.setattr(github_agent, "get_llm", lambda model=None: SlowLLM())
    result = await github_agent.answer("any recent commits?")
    assert "took longer than" in result["answer"]


@pytest.mark.asyncio
async def test_answer_synthesizes_from_fetched_commits(monkeypatch):
    monkeypatch.setattr(
        github_agent,
        "settings",
        _settings_with(github_repo="coroot/coroot", github_token="fake"),
    )

    async def fake_fetch():
        return (
            "2026-01-01T00:00:00Z",
            '[{"sha": "abc123", "commit": {"message": "fix cache bug"}}]',
        )

    monkeypatch.setattr(github_agent, "_fetch_recent_commits", fake_fetch)

    class FakeLLM:
        async def ainvoke(self, prompt):
            assert "fix cache bug" in prompt
            response = AsyncMock()
            response.content = "The cache fix commit likely explains it."
            return response

    monkeypatch.setattr(github_agent, "get_llm", lambda model=None: FakeLLM())
    result = await github_agent.answer("any recent changes explaining a regression?")
    assert result["answer"] == "The cache fix commit likely explains it."
    assert result["sources"] == ["coroot/coroot"]


@pytest.mark.asyncio
async def test_list_commits_tool_not_found_raises():
    with patch("api.agents.github_agent._mcp_client") as mock_client_factory:
        mock_client = mock_client_factory.return_value
        mock_client.get_tools = AsyncMock(return_value=[])
        with pytest.raises(RuntimeError, match="list_commits"):
            await github_agent._list_commits_tool()
