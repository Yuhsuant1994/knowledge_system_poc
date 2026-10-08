import re

import requests

from api.config import settings

API_BASE = "https://api.github.com"
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)


def _raw_url(path: str) -> str:
    """Build the raw.githubusercontent.com URL for a file in the HR source repo.

    Args:
        path: Repo-relative path to the file.

    Returns:
        The raw content URL for the file.
    """
    return f"https://raw.githubusercontent.com/{settings.hr_source_repo}/{settings.hr_source_branch}/{path}"


def page_url(path: str) -> str:
    """Convert a repo content path into its published posthog.com page URL.

    Args:
        path: Repo-relative content path, e.g. "contents/handbook/foo.md".

    Returns:
        The corresponding posthog.com page URL.
    """
    slug = path.removeprefix("contents/").rsplit(".", 1)[0]
    return f"https://posthog.com/{slug}"


def list_docs() -> list[dict]:
    """List markdown docs under the configured HR source path.

    Fetches the full git tree for the configured branch, then filters to
    Markdown/MDX files under the configured source path, excluding any
    files within "_snippets" directories.

    Returns:
        A list of dicts with "path" (repo-relative path) and "url"
        (published page URL) for each matching doc.
    """
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
    """Fetch the raw text content of a doc from the HR source repo.

    Args:
        path: Repo-relative path to the file.

    Returns:
        The raw text content of the file.
    """
    return requests.get(_raw_url(path), timeout=30).text


def extract_title(content: str, fallback: str) -> str:
    """Extract the title from a doc's YAML frontmatter, if present.

    Args:
        content: The doc's raw text content.
        fallback: Value to return if no frontmatter title is found.

    Returns:
        The frontmatter "title:" value, or ``fallback`` if the content
        has no frontmatter or no title line.
    """
    match = FRONTMATTER_RE.match(content)
    if not match:
        return fallback
    for line in match.group(1).splitlines():
        if line.startswith("title:"):
            return line.split(":", 1)[1].strip()
    return fallback
