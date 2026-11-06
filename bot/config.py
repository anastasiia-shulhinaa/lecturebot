"""Application settings read from environment variables (and a local .env file)."""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when a required setting is missing or invalid."""


# Gemini variants that produce speech, images or embeddings instead of text.
_NON_TEXT_MODEL_KINDS = ("-tts", "-image", "-live", "embedding")


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str

    google_cloud_project: str | None
    google_cloud_location: str
    gcs_bucket: str

    gemini_backend: str  # "vertex" (Google Cloud credits) or "aistudio" (API key)
    gemini_model: str
    gemini_fallback_models: list[str]  # tried in order when the main model is overloaded
    gemini_api_key: str | None

    youtube_api_key: str | None

    speech_language: str
    speech_alt_languages: list[str]

    output_language: str
    quiz_questions: int
    max_audio_minutes: int
    youtube_max_minutes: int
    max_transcript_chars: int

    webhook_url: str | None
    webhook_secret: str | None
    port: int


def _get(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or default


def _require(name: str) -> str:
    value = _get(name)
    if not value:
        raise ConfigError(f"Missing required environment variable {name} (see .env.example)")
    return value


def _list(name: str, default: str) -> list[str]:
    """A comma-separated setting; set it to an empty value to get an empty list."""
    raw = os.environ.get(name)
    raw = default if raw is None else raw
    return [item.strip() for item in raw.split(",") if item.strip()]


def _int(name: str, default: int) -> int:
    raw = _get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


@lru_cache
def get_settings() -> Settings:
    load_dotenv()

    backend = (_get("GEMINI_BACKEND", "vertex") or "vertex").lower()
    if backend not in ("vertex", "aistudio"):
        raise ConfigError("GEMINI_BACKEND must be 'vertex' or 'aistudio'")

    project = _get("GOOGLE_CLOUD_PROJECT")
    if backend == "vertex" and not project:
        raise ConfigError("GOOGLE_CLOUD_PROJECT is required when GEMINI_BACKEND=vertex")
    gemini_api_key = _get("GEMINI_API_KEY")
    if backend == "aistudio" and not gemini_api_key:
        raise ConfigError("GEMINI_API_KEY is required when GEMINI_BACKEND=aistudio")

    gemini_model = _get("GEMINI_MODEL", "gemini-3.5-flash")
    fallback_models = _list("GEMINI_FALLBACK_MODELS", "gemini-3.5-flash")
    for model in [gemini_model, *fallback_models]:
        if any(kind in model for kind in _NON_TEXT_MODEL_KINDS):
            raise ConfigError(
                f"{model} does not generate text answers; use a text model such as gemini-3.8-flash"
            )

    return Settings(
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        google_cloud_project=project,
        google_cloud_location=_get("GOOGLE_CLOUD_LOCATION", "global"),
        gcs_bucket=_require("GCS_BUCKET"),
        gemini_backend=backend,
        gemini_model=gemini_model,
        gemini_fallback_models=[model for model in fallback_models if model != gemini_model],
        gemini_api_key=gemini_api_key,
        youtube_api_key=_get("YOUTUBE_API_KEY"),
        speech_language=_get("SPEECH_LANGUAGE", "uk-UA"),
        speech_alt_languages=_list("SPEECH_ALT_LANGUAGES", "en-US")[:3],
        output_language=_get("OUTPUT_LANGUAGE", "українська"),
        quiz_questions=_int("QUIZ_QUESTIONS", 5),
        max_audio_minutes=_int("MAX_AUDIO_MINUTES", 90),
        youtube_max_minutes=_int("YOUTUBE_MAX_MINUTES", 60),
        max_transcript_chars=_int("MAX_TRANSCRIPT_CHARS", 300_000),
        webhook_url=_get("WEBHOOK_URL"),
        webhook_secret=_get("WEBHOOK_SECRET"),
        port=_int("PORT", 8080),
    )
