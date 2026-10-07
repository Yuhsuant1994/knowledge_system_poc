import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://knowledge_system:changeme@localhost:5432/knowledge_system",
    )
    sales_readonly_database_url: str = os.getenv(
        "SALES_READONLY_DATABASE_URL",
        "postgresql+psycopg2://sales_readonly:sales_readonly@localhost:5432/knowledge_system",
    )
    # --- LLM setup---#
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
    ollama_num_ctx: int = int(os.getenv("OLLAMA_NUM_CTX", "16384"))

    # --- Embedding setup---#
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "768"))

    # --- GIT setup---#
    github_token: str = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
    github_repo: str = os.getenv("GITHUB_REPO", "coroot/coroot")
    mcp_github_command: str = os.getenv("MCP_GITHUB_COMMAND", "github-mcp-server")
    mcp_github_args: str = os.getenv("MCP_GITHUB_ARGS", "stdio")

    # --- sales agent setup---#
    sales_tables: tuple = (
        "customers",
        "employees",
        "order_details",
        "orders",
        "products",
        "suppliers",
    )

    # --- hr agent setup---#
    hr_source_repo: str = os.getenv("HR_SOURCE_REPO", "PostHog/posthog.com")
    hr_source_branch: str = os.getenv("HR_SOURCE_BRANCH", "master")
    hr_source_path: str = os.getenv("HR_SOURCE_PATH", "contents/handbook/company")
    hr_update_lookback_days: int = int(os.getenv("HR_UPDATE_LOOKBACK_DAYS", "2"))

    # --- log setup---#
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_dir: str = os.getenv("LOG_DIR", "logs")
    role_cache_ttl_seconds: int = int(os.getenv("ROLE_CACHE_TTL_SECONDS", "3600"))


settings = Settings()
