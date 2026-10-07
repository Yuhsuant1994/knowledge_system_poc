import re

import requests

from api.config import settings

API_BASE = "https://api.github.com"
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


def _raw_url(path: str) -> str:
    return f"https://raw.githubusercontent.com/{settings.hr_source_repo}/{settings.hr_source_branch}/{path}"


def page_url(path: str) -> str:
    slug = path.removeprefix("contents/").rsplit(".", 1)[0]
    return f"https://posthog.com/{slug}"


def list_docs() -> list[dict]:
    url = f"{API_BASE}/repos/{settings.hr_source_repo}/git/trees/{settings.hr_source_branch}"
    tree = requests.get(url, params={"recursive": "1"}, timeout=30).json()["tree"]

    docs = []
    for item in tree:
        path = item["path"]
        if not path.startswith(settings.hr_source_path):
            continue
        if not (path.endswith(".md") or path.endswith(".mdx")):
            continue
        if "_snippets" in path.split("/"):
            continue
        docs.append({"path": path, "url": page_url(path)})
    return docs


def fetch_doc(path: str) -> str:
    return requests.get(_raw_url(path), timeout=30).text


def extract_title(content: str, fallback: str) -> str:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return fallback
    for line in match.group(1).splitlines():
        if line.startswith("title:"):
            return line.split(":", 1)[1].strip()
    return fallback
