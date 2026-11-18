"""Tests for typed tool errors and environment settings."""

from types import SimpleNamespace

from stayline.agent.llm import OpenRouterLLM
from stayline.config import load_settings
from stayline.servers.results import ToolError, parse_tool_error, tool_error


def test_tool_error_round_trip():
    err = tool_error("stale_version", "Contract changed.", retryable=True)

    assert parse_tool_error(str(err)) == ToolError(
        code="stale_version", message="Contract changed.", retryable=True
    )
    assert parse_tool_error(f"Error executing tool x: {err}") == ToolError(
        code="stale_version", message="Contract changed.", retryable=True
    )


def test_unreadable_error_becomes_internal():
    assert parse_tool_error("Traceback (most recent call last)").code == "internal"
    assert parse_tool_error("Error: {bad json}").code == "internal"


def test_settings_defaults(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for name in (
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "OPENROUTER_BASE_URL",
        "OPENROUTER_MAX_TOKENS",
        "STAYLINE_DB",
        "STAYLINE_MEMORY_DB",
        "STAYLINE_CHECKPOINT_DB",
        "STAYLINE_FAULT",
        "PHOENIX_ENDPOINT",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")

    settings = load_settings()

    assert settings.api_key.get_secret_value() == "k"
    assert settings.model == "~deepseek/deepseek-v4-flash-latest"
    assert settings.base_url == "https://openrouter.ai/api/v1"
    assert settings.db_path == "stayline.sqlite"
    assert settings.memory_db_path == "stayline-memory.sqlite"
    assert settings.checkpoint_db_path == "stayline-checkpoints.sqlite"
    assert settings.insurer_id == "STAYLINE-VIE"
    assert settings.max_model_calls == 12
    assert settings.max_tokens == 4000
    assert settings.tool_timeout_s == 10.0
    assert settings.model_timeout_s == 90.0
    assert settings.phoenix_endpoint is None


def test_settings_overrides_win_over_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENROUTER_MODEL", "environment-model")
    monkeypatch.setenv("STAYLINE_DB", "environment.sqlite")
    monkeypatch.setenv("STAYLINE_FAULT", "rate_limit")
    monkeypatch.setenv("OPENROUTER_MAX_TOKENS", "5000")

    from_environment = load_settings()
    settings = load_settings(model="override-model", db_path="override.sqlite", max_tokens=6000)

    assert from_environment.max_tokens == 5000
    assert settings.max_tokens == 6000
    assert settings.model == "override-model"
    assert settings.db_path == "override.sqlite"
    assert settings.fault == "rate_limit"


async def test_model_uses_configured_reply_budget():
    settings = load_settings(max_tokens=6000)
    model = OpenRouterLLM(settings)
    captured = {}

    async def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(
                model_dump=lambda **_: {"role": "assistant", "content": "ok"},
            ))],
            usage=SimpleNamespace(prompt_tokens=2, completion_tokens=1),
            model="fake-model",
        )

    model.client = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=create),
    ))
    await model.complete([{"role": "user", "content": "hi"}], [])

    assert captured["max_tokens"] == 6000


def test_settings_repr_hides_api_key(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sensitive-test-key")

    assert "sensitive-test-key" not in repr(load_settings())
