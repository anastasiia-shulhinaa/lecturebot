import pytest

from bot import config
from bot.config import ConfigError, get_settings


@pytest.fixture
def env(monkeypatch):
    # Never read the developer's real .env in tests.
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    for name in ("GEMINI_MODEL", "GEMINI_FALLBACK_MODELS", "GEMINI_API_KEY", "SPEECH_ALT_LANGUAGES"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")
    monkeypatch.setenv("GCS_BUCKET", "demo-bucket")
    monkeypatch.setenv("GEMINI_BACKEND", "vertex")
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def test_fallback_models(env):
    env.setenv("GEMINI_MODEL", "gemini-3.8-flash")
    env.setenv("GEMINI_FALLBACK_MODELS", " gemini-3.5-flash , gemini-3.8-flash ")
    settings = get_settings()
    assert settings.gemini_model == "gemini-3.8-flash"
    # The main model is not repeated as its own fallback.
    assert settings.gemini_fallback_models == ["gemini-3.5-flash"]


def test_fallback_models_can_be_disabled(env):
    env.setenv("GEMINI_FALLBACK_MODELS", "")
    assert get_settings().gemini_fallback_models == []


@pytest.mark.parametrize("model", ["gemini-3.8-flash-lite-tts", "gemini-3.5-flash-image", "gemini-embedding-001"])
def test_non_text_models_are_rejected(env, model):
    env.setenv("GEMINI_MODEL", model)
    with pytest.raises(ConfigError):
        get_settings()


def test_alt_languages_are_capped_at_three(env):
    env.setenv("SPEECH_ALT_LANGUAGES", "en-US, de-DE,pl-PL,fr-FR")
    assert get_settings().speech_alt_languages == ["en-US", "de-DE", "pl-PL"]
