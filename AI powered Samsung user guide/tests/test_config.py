import pytest

from core import config
from core.config import ConfigError, load_settings


def test_missing_key_raises_actionable_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    with pytest.raises(ConfigError, match=".env.example"):
        load_settings()


def test_key_optional_for_storage_only_tools(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    assert load_settings(require_api_key=False).gemini_api_key == ""


def test_defaults(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.delenv("EMBED_MODEL", raising=False)
    monkeypatch.delenv("GEN_MODEL", raising=False)
    monkeypatch.delenv("DATA_ROOT", raising=False)
    s = load_settings()
    assert s.embed_model == "gemini-embedding-001"
    # Pinned, not an alias like gemini-flash-latest: the eval numbers in
    # eval/RESULTS.md are only reproducible against a fixed model.
    assert s.gen_model == "gemini-3.7-flash"
    assert s.store_dir == s.data_root / "store"
    assert s.raw_dir == s.data_root / "raw"


def test_relative_data_root_resolves_against_project(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("DATA_ROOT", "somewhere")
    assert load_settings().data_root == config.PROJECT_ROOT / "somewhere"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("GEN_MODEL", "gemini-2.5-pro")
    assert load_settings().gen_model == "gemini-2.5-pro"


def test_catalog_lives_outside_the_swapped_store(monkeypatch):
    """Regression: `manifest.json` once lived in `store_dir`, which is replaced
    wholesale on every re-index — so building the store deleted the manifest the
    next build needed to find its manuals. The build destroyed its own input."""
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    s = load_settings()
    assert s.catalog_dir != s.store_dir
    assert s.store_dir not in s.catalog_dir.parents
    assert s.catalog_dir not in s.store_dir.parents
