"""Check that every key, permission and tool the bot needs works: `python -m bot.check_setup`.

Each check makes one tiny real request (well within the free tiers) and prints a hint on failure.
"""

import asyncio
import logging
import sys
import tempfile
import uuid
from pathlib import Path

from bot.config import ConfigError, Settings, get_settings


def check_ffmpeg(settings: Settings) -> str:
    from bot.media_utils import ensure_ffmpeg

    ensure_ffmpeg()
    return "ffmpeg and ffprobe found"


def check_telegram(settings: Settings) -> str:
    from telegram import Bot

    async def get_me():
        async with Bot(settings.telegram_bot_token) as bot:
            return await bot.get_me()

    return f"bot @{asyncio.run(get_me()).username}"


def check_credentials(settings: Settings) -> str:
    import google.auth

    credentials, project = google.auth.default()
    quota = getattr(credentials, "quota_project_id", None)
    return f"default project={project}, quota project={quota}"


def check_storage(settings: Settings) -> str:
    from bot.storage import AudioStorage

    storage = AudioStorage(settings.google_cloud_project, settings.gcs_bucket)
    blob_name = f"setup-check/{uuid.uuid4().hex}.txt"
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "check.txt"
        path.write_text("ok")
        uri = storage.upload(path, blob_name)
    storage.delete(blob_name)
    return f"uploaded and deleted {uri}"


def check_speech(settings: Settings) -> str:
    from google.cloud import speech

    response = speech.SpeechClient().recognize(
        config=speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16_000,
            language_code=settings.speech_language,
        ),
        audio=speech.RecognitionAudio(content=b"\0" * 32_000),  # 1 s of silence
    )
    return f"API reachable ({len(response.results)} results for silence, as expected)"


def check_gemini(settings: Settings) -> str:
    from bot.gemini_service import GeminiService

    answer = asyncio.run(
        GeminiService(settings).answer(
            "Хмарні обчислення — це надання обчислювальних ресурсів через інтернет.",
            "Що таке хмарні обчислення? Одне коротке речення.",
        )
    )
    return f"model answered: {answer[:80]}"


def check_youtube(settings: Settings) -> str:
    from bot.youtube_service import YouTubeService

    info = YouTubeService(settings.youtube_api_key).get_video("dQw4w9WgXcQ")
    return f"test video: {info.title}" if info else "API works, test video not found"


def check_gemini_youtube(settings: Settings) -> str:
    from bot.gemini_service import GeminiService

    # "Me at the zoo": the first YouTube video, 19 seconds long, so the check costs almost nothing.
    text = asyncio.run(GeminiService(settings).transcribe_youtube("https://www.youtube.com/watch?v=jNQXAC9IVRw"))
    return f"video read: {text[:60]}"


CHECKS = [
    ("FFmpeg", check_ffmpeg,
     "winget install Gyan.FFmpeg, then open a NEW terminal"),
    ("Telegram bot token", check_telegram,
     "copy the token from @BotFather into TELEGRAM_BOT_TOKEN"),
    ("Google credentials", check_credentials,
     "run: gcloud auth application-default login, then "
     "gcloud auth application-default set-quota-project <PROJECT_ID>"),
    ("Cloud Storage bucket", check_storage,
     "GCS_BUCKET must be the exact bucket name; Cloud Storage API must be enabled"),
    ("Speech-to-Text API", check_speech,
     "enable 'Cloud Speech-to-Text API' and set the quota project (see Google credentials)"),
    ("Gemini", check_gemini,
     "403: enable 'Vertex AI API'; 404 NOT_FOUND: pick another GEMINI_MODEL in Model Garden "
     "or set GOOGLE_CLOUD_LOCATION=us-central1; 400 INVALID_ARGUMENT: GEMINI_MODEL must be "
     "a text model such as gemini-3.8-flash"),
    ("YouTube Data API v3", check_youtube,
     "enable 'YouTube Data API v3'; the key must be restricted to that API"),
    ("Gemini + YouTube video", check_gemini_youtube,
     "401: Vertex AI can't open YouTube links, so add an AI Studio key to GEMINI_API_KEY "
     "(SETUP.md, Part 7, Option B); 402 'prepayment credits are depleted': the key's project has "
     "billing, so create the key in a NEW project without billing (free tier); 429 'limit: 0': "
     "this model isn't in the free tier"),
]


def main() -> None:
    # The services log full tracebacks on failure; here one line per check is enough.
    logging.disable(logging.CRITICAL)
    try:
        settings = get_settings()
    except ConfigError as exc:
        print(f"[FAIL] .env settings - {exc}\n       Hint: copy .env.example to .env and fill it in")
        sys.exit(1)
    print(f"[OK] .env settings - project={settings.google_cloud_project}, "
          f"gemini={settings.gemini_backend}/{settings.gemini_model}, "
          f"fallback={', '.join(settings.gemini_fallback_models) or 'none'}, "
          f"youtube via {'AI Studio key' if settings.gemini_api_key else settings.gemini_backend}")

    failed = 0
    for name, func, hint in CHECKS:
        if func in (check_youtube, check_gemini_youtube) and not settings.youtube_api_key:
            print(f"[SKIP] {name} - YOUTUBE_API_KEY is empty, YouTube links will be disabled")
            continue
        try:
            print(f"[OK] {name} - {func(settings)}")
        except Exception as exc:  # report every failure and keep checking the rest
            failed += 1
            # User-facing errors wrap the real API error; show that one.
            cause = exc.__cause__ or exc
            print(f"[FAIL] {name} - {type(cause).__name__}: {cause}\n       Hint: {hint}")

    print()
    if failed:
        print(f"{failed} check(s) failed. Fix them using the hints above and run this again.")
        sys.exit(1)
    print("All checks passed. Start the bot with: python -m bot.main")


if __name__ == "__main__":
    main()
