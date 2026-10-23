"""Central configuration, loaded from environment variables / a `.env` file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Export .env into os.environ so provider keys (GEMINI_API_KEY, ...) reach LiteLLM, the API,
# the Chainlit UI and the eval runner. Real environment variables still take precedence.
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", env_prefix="HELPDESK_", extra="ignore"
    )

    # --- LLM (any LiteLLM model string: gemini/..., azure/..., openai/..., ollama/...) ---
    llm_model: str = "gemini/gemini-3.5-flash"
    judge_model: str | None = None  # defaults to llm_model
    llm_temperature: float = 0.1
    llm_timeout_s: float = 60.0
    # Minimum seconds between LLM calls to one model (free tiers: 13 keeps under 5 req/min).
    llm_min_interval_s: float = 0.0

    # --- Retrieval ---
    kb_dir: Path = PROJECT_ROOT / "data" / "kb"
    qdrant_path: Path = PROJECT_ROOT / ".data" / "qdrant"
    qdrant_url: str | None = None  # set to use a Qdrant server instead of embedded mode
    collection: str = "helpdesk_kb"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    use_reranker: bool = True
    top_k: int = 4
    candidate_k: int = 20
    chunk_max_chars: int = 1200

    # --- Storage ---
    tickets_db: Path = PROJECT_ROOT / ".data" / "tickets.db"
    telemetry_db: Path = PROJECT_ROOT / ".data" / "telemetry.db"

    # --- Agent ---
    max_agent_steps: int = 6
    tool_backend: str = "mcp"  # "mcp" (spawn MCP server over stdio) or "local" (in-process)

    @property
    def resolved_judge_model(self) -> str:
        return self.judge_model or self.llm_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
