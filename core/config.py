"""Settings, loaded from the environment (and .env if present)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or unusable."""


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    embed_model: str = "gemini-embedding-001"
    # Embeddings run locally by default: Gemini's free tier allows 1,000 items
    # per day and the corpus needs 4,630. Generation still goes to Gemini, which
    # is well inside its own free-tier limits.
    embed_backend: str = "local"  # "local" | "gemini"
    local_embed_model: str = "BAAI/bge-small-en-v1.5"
    gen_model: str = "gemini-2.5-flash"
    # Reranking is off by default. Measured on 54 questions it bought +0.02
    # Recall@1 while *losing* 0.02 Recall@5, left MRR flat (0.844 -> 0.840), and
    # cost 280x latency (56ms -> 15.6s p50). A 15-second wait before generation
    # even starts is not viable for a chat UI. See eval/RESULTS.md.
    rerank_enabled: bool = False
    rerank_model: str = "BAAI/bge-reranker-base"
    data_root: Path = PROJECT_ROOT / "data"
    log_level: str = "INFO"

    @property
    def raw_dir(self) -> Path:
        return self.data_root / "raw"

    @property
    def store_dir(self) -> Path:
        """The searchable index. Rebuilt from scratch and swapped in atomically,
        so nothing that cannot be regenerated may live here."""
        return self.data_root / "store"

    @property
    def catalog_dir(self) -> Path:
        """Acquisition state: `manifest.json`, `coverage.json`.

        Deliberately outside `store_dir`. That directory is replaced wholesale on
        every re-index, which would delete the very manifest the next build reads
        to find its manuals — the build would destroy its own input.
        """
        return self.data_root / "catalog"


def load_settings(require_api_key: bool = True) -> Settings:
    """Build Settings from the environment.

    Ingestion and query both need the API key; storage-level tooling does not,
    hence `require_api_key`.
    """
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if require_api_key and not key:
        raise ConfigError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    data_root = Path(os.environ.get("DATA_ROOT") or (PROJECT_ROOT / "data"))
    if not data_root.is_absolute():
        data_root = PROJECT_ROOT / data_root

    return Settings(
        gemini_api_key=key,
        embed_model=os.environ.get("EMBED_MODEL", "gemini-embedding-001"),
        embed_backend=os.environ.get("EMBED_BACKEND", "local").lower(),
        local_embed_model=os.environ.get("LOCAL_EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
        gen_model=os.environ.get("GEN_MODEL", "gemini-2.5-flash"),
        rerank_enabled=os.environ.get("RERANK", "").lower() in ("1", "true", "yes"),
        rerank_model=os.environ.get("RERANK_MODEL", "BAAI/bge-reranker-base"),
        data_root=data_root,
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    )
