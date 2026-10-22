"""Entry point: `python -m bot.main`.

Locally the bot uses long polling. When WEBHOOK_URL is set (Cloud Run), it serves a webhook.
"""

import logging
import sys

from google.auth.exceptions import DefaultCredentialsError
from telegram import BotCommand, Update
from telegram.ext import Application

from bot import handlers, media_utils
from bot.config import ConfigError, Settings, get_settings
from bot.gemini_service import GeminiService
from bot.speech_to_text import SpeechTranscriber
from bot.storage import AudioStorage
from bot.youtube_service import YouTubeService

logger = logging.getLogger("lecturebot")

WEBHOOK_PATH = "telegram"

COMMANDS = [
    BotCommand("start", "Почати роботу"),
    BotCommand("help", "Інструкція"),
    BotCommand("new", "Обробити нову лекцію"),
]


async def _post_init(application: Application) -> None:
    await application.bot.set_my_commands(COMMANDS)


def build_application(settings: Settings) -> Application:
    storage = AudioStorage(settings.google_cloud_project, settings.gcs_bucket)
    services = handlers.Services(
        settings=settings,
        transcriber=SpeechTranscriber(storage, settings.speech_language, settings.speech_alt_languages),
        gemini=GeminiService(settings),
        youtube=YouTubeService(settings.youtube_api_key) if settings.youtube_api_key else None,
    )
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .concurrent_updates(True)
        .post_init(_post_init)
        .build()
    )
    application.bot_data["services"] = services
    handlers.register(application)
    return application


def main() -> None:
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
    # httpx logs every request URL, and Telegram URLs contain the bot token.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    try:
        settings = get_settings()
        media_utils.ensure_ffmpeg()
        application = build_application(settings)
    except ConfigError as exc:
        sys.exit(f"Configuration error: {exc}")
    except DefaultCredentialsError:
        sys.exit(
            "Google Cloud credentials not found. Run:\n"
            "  gcloud auth application-default login\n"
            "  gcloud auth application-default set-quota-project <PROJECT_ID>"
        )
    except RuntimeError as exc:
        sys.exit(str(exc))

    if settings.webhook_url:
        logger.info("Starting in webhook mode on port %s", settings.port)
        application.run_webhook(
            listen="0.0.0.0",
            port=settings.port,
            url_path=WEBHOOK_PATH,
            webhook_url=f"{settings.webhook_url.rstrip('/')}/{WEBHOOK_PATH}",
            secret_token=settings.webhook_secret,
            allowed_updates=Update.ALL_TYPES,
        )
    else:
        logger.info("Starting in polling mode. Press Ctrl+C to stop.")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
