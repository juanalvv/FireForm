"""Unit tests for the centralised config module."""

import importlib
import os
from pathlib import Path

import pytest


def _reload_config(env_overrides: dict | None = None):
    """Reload ``config`` with optional env-var overrides."""
    env_overrides = env_overrides or {}
    old_values = {}
    for key, value in env_overrides.items():
        old_values[key] = os.environ.get(key)
        os.environ[key] = value

    try:
        import config
        importlib.reload(config)
        return config
    finally:
        for key, old in old_values.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


# ── Default values ───────────────────────────────────────────────────

class TestDefaults:
    def test_ollama_host_default(self):
        cfg = _reload_config()
        assert cfg.OLLAMA_HOST == "http://localhost:11434"

    def test_ollama_model_default(self):
        cfg = _reload_config()
        assert cfg.OLLAMA_MODEL == "mistral"

    def test_ollama_api_path_default(self):
        cfg = _reload_config()
        assert cfg.OLLAMA_API_PATH == "/api/generate"

    def test_output_pdf_suffix_default(self):
        cfg = _reload_config()
        assert cfg.OUTPUT_PDF_SUFFIX == "_filled.pdf"


# ── Env-var overrides ────────────────────────────────────────────────

class TestEnvOverrides:
    def test_ollama_host_override(self):
        cfg = _reload_config({"OLLAMA_HOST": "http://my-server:9999"})
        assert cfg.OLLAMA_HOST == "http://my-server:9999"

    def test_ollama_model_override(self):
        cfg = _reload_config({"OLLAMA_MODEL": "llama3"})
        assert cfg.OLLAMA_MODEL == "llama3"

    def test_ollama_api_path_override(self):
        cfg = _reload_config({"OLLAMA_API_PATH": "/v2/generate"})
        assert cfg.OLLAMA_API_PATH == "/v2/generate"

    def test_output_pdf_suffix_override(self):
        cfg = _reload_config({"OUTPUT_PDF_SUFFIX": "_output.pdf"})
        assert cfg.OUTPUT_PDF_SUFFIX == "_output.pdf"

    def test_ollama_host_trailing_slash_stripped(self):
        cfg = _reload_config({"OLLAMA_HOST": "http://my-server:9999/"})
        assert cfg.OLLAMA_HOST == "http://my-server:9999"


# ── Path values ──────────────────────────────────────────────────────

class TestPaths:
    def test_base_dir_is_src(self):
        cfg = _reload_config()
        assert cfg.BASE_DIR.name == "src"
        assert cfg.BASE_DIR.is_dir()

    def test_default_input_pdf_path(self):
        cfg = _reload_config()
        assert cfg.DEFAULT_INPUT_PDF == cfg.BASE_DIR / "inputs" / "file.pdf"

    def test_default_prepared_pdf_path(self):
        cfg = _reload_config()
        assert cfg.DEFAULT_PREPARED_PDF == cfg.BASE_DIR / "temp_outfile.pdf"

    def test_paths_are_path_objects(self):
        cfg = _reload_config()
        assert isinstance(cfg.BASE_DIR, Path)
        assert isinstance(cfg.DEFAULT_INPUT_PDF, Path)
        assert isinstance(cfg.DEFAULT_PREPARED_PDF, Path)
