"""Telegram handlers: commands, file intake, YouTube links, buttons and Q&A."""

import asyncio
import html
import logging
import tempfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Poll, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot import media_utils
from bot.config import Settings
from bot.errors import UserFacingError
from bot.gemini_service import GeminiService
from bot.schemas import POLL_QUESTION_LIMIT
from bot.speech_to_text import SpeechTranscriber
from bot.text_utils import clip, format_duration, html_to_plain, markdown_to_telegram_html, split_text
from bot.youtube_service import YouTubeService, extract_video_id

logger = logging.getLogger(__name__)

# The cloud Bot API lets bots download files up to 20 MB.
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024

BUSY = "busy"
TRANSCRIPT = "transcript"
TITLE = "title"
PENDING_YOUTUBE = "pending_youtube"

START_TEXT = (
    "👋 Привіт! Я <b>LectureBot</b>.\n\n"
    "Надішліть мені запис лекції, і я зроблю з нього <b>конспект</b> і <b>тест</b> "
    "для самоперевірки, а ще відповім на запитання за матеріалом."
)

SOURCES_TEXT = (
    "Надішліть один із варіантів:\n"
    "🎤 голосове повідомлення;\n"
    "🎧 аудіофайл (MP3, M4A, OGG, WAV…);\n"
    "🎬 відео або кружечок;\n"
    "🔗 посилання на публічне YouTube-відео.\n\n"
    "Розмір файлу — до 20 МБ (обмеження Telegram). Для довгих лекцій надсилайте аудіо: "
    "20 МБ у MP3 — це приблизно 40–80 хвилин."
)

HELP_TEXT = (
    "<b>Як це працює</b>\n"
    "1. Надішліть запис або YouTube-посилання.\n"
    "2. Google Cloud Speech-to-Text перетворює мовлення на текст "
    "(для YouTube відео аналізує Gemini).\n"
    "3. Оберіть, що створити: короткий переказ, конспект, тест або конспект + тест.\n"
    "4. Ставте запитання за лекцією звичайним повідомленням.\n\n"
    "<b>Команди</b>\n"
    "/start — початок роботи\n"
    "/new — обробити нову лекцію\n"
    "/help — ця довідка\n\n"
    "🔒 Файли обробляються сервісами Google Cloud і видаляються одразу після транскрибування. "
    "Транскрипт зберігається лише в пам'яті бота до команди /new.\n\n"
    "⚠️ Конспект і тест створюються автоматично й можуть містити помилки — перевіряйте їх."
)

BUSY_TEXT = "⏳ Зачекайте, попередній запит ще обробляється."
NO_LECTURE_TEXT = "Спочатку надішліть лекцію: аудіо, відео або YouTube-посилання."
GENERIC_ERROR_TEXT = "⚠️ Сталася помилка під час обробки. Спробуйте ще раз трохи згодом."

ACTIONS_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("⚡ Коротко", callback_data="brief"),
            InlineKeyboardButton("📝 Конспект", callback_data="summary"),
        ],
        [
            InlineKeyboardButton("❓ Тест", callback_data="quiz"),
            InlineKeyboardButton("📚 Конспект + тест", callback_data="both"),
        ],
        [InlineKeyboardButton("📄 Транскрипт", callback_data="transcript")],
    ]
)


@dataclass
class Services:
    settings: Settings
    transcriber: SpeechTranscriber
    gemini: GeminiService
    youtube: YouTubeService | None


def register(application: Application) -> None:
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("new", new_command))
    application.add_handler(
        MessageHandler(
            filters.VOICE | filters.AUDIO | filters.VIDEO | filters.VIDEO_NOTE
            | filters.Document.AUDIO | filters.Document.VIDEO,
            on_media,
        )
    )
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    application.add_handler(CallbackQueryHandler(on_new_button, pattern="^new$"))
    application.add_handler(CallbackQueryHandler(on_youtube_button, pattern="^yt:"))
    application.add_handler(CallbackQueryHandler(on_action, pattern="^(brief|summary|quiz|both|transcript)$"))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, on_unsupported))
    application.add_error_handler(on_error)


def _services(context: ContextTypes.DEFAULT_TYPE) -> Services:
    return context.application.bot_data["services"]


# --- Commands -----------------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📚 Обробити лекцію", callback_data="new")]])
    await update.effective_message.reply_text(START_TEXT, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reset_session(update.effective_message, context)


async def on_new_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await _reset_session(update.callback_query.message, context)


async def _reset_session(message: Message, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get(BUSY):
        await message.reply_text(BUSY_TEXT)
        return
    context.user_data.clear()
    await message.reply_text(SOURCES_TEXT)


# --- Jobs ---------------------------------------------------------------------


async def _run_job(
    message: Message,
    context: ContextTypes.DEFAULT_TYPE,
    status_text: str,
    work: Callable[[Message], Awaitable[None]],
) -> None:
    """Run one long task per user, with a status message and friendly errors."""
    if context.user_data.get(BUSY):
        await message.reply_text(BUSY_TEXT)
        return
    context.user_data[BUSY] = True
    status = await message.reply_text(status_text)
    try:
        await work(status)
    except UserFacingError as exc:
        await _safe_edit(status, f"⚠️ {exc}")
    except Exception:
        logger.exception("Job failed")
        await _safe_edit(status, GENERIC_ERROR_TEXT)
    finally:
        context.user_data[BUSY] = False


async def _safe_edit(message: Message, text: str) -> None:
    try:
        await message.edit_text(text)
    except BadRequest:
        # The text did not change or the message is gone; nothing useful to do.
        pass


def _save_lecture(context: ContextTypes.DEFAULT_TYPE, transcript: str, title: str) -> None:
    context.user_data[TRANSCRIPT] = transcript
    context.user_data[TITLE] = title


async def _offer_actions(status: Message, transcript: str) -> None:
    words = len(transcript.split())
    await status.edit_text(
        f"✅ Текст лекції готовий ({words} слів).\n\n"
        "Що створити? Або просто напишіть запитання за лекцією.",
        reply_markup=ACTIONS_KEYBOARD,
    )


# --- Files ----------------------------------------------------------------------


def _media_of(message: Message):
    for media in (message.voice, message.audio, message.video, message.video_note, message.document):
        if media:
            return media
    return None


async def on_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    media = _media_of(message)
    if media.file_size and media.file_size > MAX_DOWNLOAD_BYTES:
        await message.reply_text(
            "📦 Файл більший за 20 МБ — Telegram не дає ботам завантажувати такі файли.\n"
            "Надішліть лише аудіо (наприклад, MP3) або коротший фрагмент."
        )
        return

    title = getattr(media, "file_name", None) or getattr(media, "title", None) or "Лекція"
    services = _services(context)

    async def work(status: Message) -> None:
        with tempfile.TemporaryDirectory(prefix="lecturebot_") as tmp:
            source = Path(tmp) / "input"
            try:
                telegram_file = await context.bot.get_file(media.file_id)
            except BadRequest as exc:
                raise UserFacingError("Не вдалося завантажити файл: він завеликий для бота (понад 20 МБ).") from exc
            await telegram_file.download_to_drive(source)

            await _safe_edit(status, "🎧 Готую аудіо…")
            flac = Path(tmp) / "audio.flac"
            await asyncio.to_thread(media_utils.convert_to_flac, source, flac)
            duration = await asyncio.to_thread(media_utils.probe_duration, flac)
            max_minutes = services.settings.max_audio_minutes
            if duration > max_minutes * 60:
                raise UserFacingError(f"Запис довший за {max_minutes} хв. Надішліть коротший фрагмент.")

            await _safe_edit(
                status,
                f"📝 Розпізнаю мовлення ({format_duration(duration)})… "
                "Для довгих записів це може тривати кілька хвилин.",
            )
            transcript = await asyncio.to_thread(services.transcriber.transcribe, flac, duration)

        _save_lecture(context, transcript, title)
        await _offer_actions(status, transcript)

    await _run_job(message, context, "📥 Файл отримано. Завантажую…", work)


async def on_unsupported(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("Такий тип повідомлення я не обробляю.\n\n" + SOURCES_TEXT)


# --- Text: YouTube links and questions ----------------------------------------------


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    video_id = extract_video_id(message.text)
    if video_id:
        await _show_youtube_card(message, context, video_id)
    elif context.user_data.get(TRANSCRIPT):
        await _answer_question(message, context)
    else:
        await message.reply_text(NO_LECTURE_TEXT + "\n\n" + SOURCES_TEXT)


async def _show_youtube_card(message: Message, context: ContextTypes.DEFAULT_TYPE, video_id: str) -> None:
    services = _services(context)
    if services.youtube is None:
        await message.reply_text("Обробку YouTube не налаштовано (немає YOUTUBE_API_KEY).")
        return
    try:
        info = await asyncio.to_thread(services.youtube.get_video, video_id)
    except UserFacingError as exc:
        await message.reply_text(f"⚠️ {exc}")
        return

    if info is None:
        await message.reply_text("Відео не знайдено. Перевірте посилання.")
        return
    if info.privacy_status != "public":
        await message.reply_text("🔒 Можна обробляти лише публічні відео.")
        return
    if info.is_live:
        await message.reply_text("📡 Трансляції не підтримуються. Надішліть посилання на звичайне відео.")
        return
    max_minutes = services.settings.youtube_max_minutes
    if info.duration_seconds > max_minutes * 60:
        await message.reply_text(f"⏱ Відео довше за {max_minutes} хв. Оберіть коротше.")
        return

    context.user_data[PENDING_YOUTUBE] = info
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("▶️ Обробити", callback_data="yt:go"),
            InlineKeyboardButton("✖️ Скасувати", callback_data="yt:cancel"),
        ]]
    )
    await message.reply_text(
        f"🎬 <b>{html.escape(info.title)}</b>\n"
        f"📺 {html.escape(info.channel)}\n"
        f"⏱ {format_duration(info.duration_seconds)}\n\n"
        "Обробити це відео?",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )


async def on_youtube_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    info = context.user_data.pop(PENDING_YOUTUBE, None)
    await query.edit_message_reply_markup(reply_markup=None)
    if query.data == "yt:cancel":
        return
    if info is None:
        await query.message.reply_text("Посилання застаріло. Надішліть його ще раз.")
        return

    services = _services(context)

    async def work(status: Message) -> None:
        transcript = await services.gemini.transcribe_youtube(info.url)
        _save_lecture(context, transcript, info.title)
        await _offer_actions(status, transcript)

    await _run_job(query.message, context, "🎬 Gemini аналізує відео… Це може тривати хвилину-дві.", work)


async def _answer_question(message: Message, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = _services(context)
    transcript = context.user_data[TRANSCRIPT]

    async def work(status: Message) -> None:
        answer = await services.gemini.answer(transcript, message.text)
        await status.delete()
        await _send_markdown(message, answer)

    await _run_job(message, context, "🤔 Шукаю відповідь у лекції…", work)


# --- Buttons: summary, quiz, transcript ---------------------------------------------


async def on_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    message = query.message
    transcript = context.user_data.get(TRANSCRIPT)
    if not transcript:
        await message.reply_text(NO_LECTURE_TEXT)
        return

    title = context.user_data.get(TITLE, "Лекція")
    action = query.data
    services = _services(context)

    if action == "transcript":
        await message.reply_document(
            document=transcript.encode("utf-8"),
            filename="transcript.txt",
            caption=f"📄 Транскрипт: {clip(title, 200)}",
        )
        return

    async def work(status: Message) -> None:
        if action == "brief":
            await _send_markdown(message, await services.gemini.summarize(transcript, brief=True))
        if action in ("summary", "both"):
            summary = await services.gemini.summarize(transcript)
            await _send_markdown(message, summary)
            await message.reply_document(
                document=f"# {title}\n\n{summary}\n".encode("utf-8"),
                filename="summary.md",
                caption="📝 Конспект файлом",
            )
        if action in ("quiz", "both"):
            await _safe_edit(status, "❓ Складаю тест…")
            questions = await services.gemini.make_quiz(transcript, services.settings.quiz_questions)
            await message.reply_text(f"❓ Тест: {len(questions)} запитань. Оберіть відповідь у кожному.")
            for number, item in enumerate(questions, start=1):
                await message.reply_poll(
                    question=clip(f"{number}. {item.question}", POLL_QUESTION_LIMIT),
                    options=item.options,
                    type=Poll.QUIZ,
                    correct_option_id=item.correct_index,
                    explanation=item.explanation or None,
                    is_anonymous=False,
                )
        await status.delete()
        await message.reply_text("Що ще зробити?", reply_markup=ACTIONS_KEYBOARD)

    status_text = {
        "brief": "⚡ Стисло переказую лекцію…",
        "quiz": "❓ Складаю тест…",
    }.get(action, "📝 Створюю конспект…")
    await _run_job(message, context, status_text, work)


async def _send_markdown(message: Message, markdown: str) -> None:
    """Send Gemini's Markdown as Telegram HTML, falling back to plain text."""
    for chunk in split_text(markdown_to_telegram_html(markdown)):
        try:
            await message.reply_text(chunk, parse_mode=ParseMode.HTML)
        except BadRequest:
            await message.reply_text(html_to_plain(chunk))


# --- Errors -----------------------------------------------------------------------


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled error", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(GENERIC_ERROR_TEXT)
        except Exception:
            logger.exception("Could not report the error to the user")
