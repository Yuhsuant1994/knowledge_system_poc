from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

from langchain_mcp_adapters.client import MultiServerMCPClient

from api.agents.llm import get_llm
from api.config import settings

MAX_COMMITS = 10
LOOKBACK_DAYS = 7
FETCH_TIMEOUT_SECONDS = 30
LLM_TIMEOUT_SECONDS = 100

# TODO: need to restrict the load size and timeout, while using small model
SYNTHESIS_PROMPT = """You are a read-only GitHub assistant for {repo}.

Commits on the default branch since {since} (newest first, up to {max_commits} shown):
{commits}

Question: {question}

Answer using only the commits above, in 2-4 sentences -- a short answer is
faster to generate and easier to read. If none look relevant, say so plainly,
don't guess about commits you can't see."""


def _mcp_client() -> MultiServerMCPClient:
    args = settings.mcp_github_args.split(",") if settings.mcp_github_args else []
    return MultiServerMCPClient(
        {
            "github": {
                "command": settings.mcp_github_command,
                "args": args,
                "transport": "stdio",
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": settings.github_token},
            }
        }
    )


async def _list_commits_tool():
    tools = await _mcp_client().get_tools()
    for tool in tools:
        if tool.name == "list_commits":
            return tool
    raise RuntimeError("GitHub MCP server doesn't expose list_commits")


def _format_commits(raw) -> str:
    return raw if isinstance(raw, str) else json.dumps(raw)


async def _fetch_recent_commits() -> str:
    owner, _, repo = settings.github_repo.partition("/")
    since = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    tool = await _list_commits_tool()
    raw = await tool.ainvoke(
        {
            "owner": owner,
            "repo": repo,
            "since": since,
            "perPage": MAX_COMMITS,
            "fields": ["sha", "commit", "html_url"],
        }
    )
    return since, _format_commits(raw)


async def answer(question: str) -> dict:
    if not settings.github_repo:
        return {"answer": "GITHUB_REPO is not configured.", "sources": []}
    if not settings.github_token:
        return {
            "answer": "GITHUB_PERSONAL_ACCESS_TOKEN is not configured.",
            "sources": [],
        }

    try:
        since, commits_text = await asyncio.wait_for(
            _fetch_recent_commits(), timeout=FETCH_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        return {
            "answer": f"Fetching commits from GitHub took longer than {FETCH_TIMEOUT_SECONDS}s.",
            "sources": [settings.github_repo],
        }
    except Exception as exc:
        return {
            "answer": f"Couldn't fetch commits from GitHub ({exc}).",
            "sources": [settings.github_repo],
        }

    prompt = SYNTHESIS_PROMPT.format(
        repo=settings.github_repo,
        since=since,
        max_commits=MAX_COMMITS,
        commits=commits_text,
        question=question,
    )
    try:
        llm = get_llm()
        response = await asyncio.wait_for(
            llm.ainvoke(prompt), timeout=LLM_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        return {
            "answer": f"The model took longer than {LLM_TIMEOUT_SECONDS}s to summarize the commits.",
            "sources": [settings.github_repo],
        }

    return {"answer": response.content, "sources": [settings.github_repo]}
