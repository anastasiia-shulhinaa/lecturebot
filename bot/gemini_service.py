"""Gemini (Google Cloud Agent Platform, formerly Vertex AI): summaries, quizzes, answers."""

import logging

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import TypeAdapter, ValidationError

from bot import prompts
from bot.config import Settings
from bot.errors import UserFacingError
from bot.schemas import QuizQuestion, sanitize_quiz

logger = logging.getLogger(__name__)

_QUIZ_ADAPTER = TypeAdapter(list[QuizQuestion])

# Overloaded (500/503) or rate-limited (429) models: fall back to the next configured model.
_TRY_NEXT_MODEL_CODES = (429, 500, 503)


def _user_facing_error(exc: genai_errors.APIError, *, youtube: bool) -> UserFacingError:
    logger.error("Gemini request failed: %s", exc)
    if exc.code == 429:
        return UserFacingError("Вичерпано квоту Gemini. Спробуйте за хвилину.")
    if exc.code == 402:
        return UserFacingError(
            "Закінчився баланс Gemini API в AI Studio. Потрібен ключ із проєкту без білінгу "
            "(безкоштовний рівень)."
        )
    if exc.code == 503:
        return UserFacingError("Gemini зараз перевантажений. Спробуйте ще раз за хвилину.")
    if youtube and exc.code in (401, 403):
        return UserFacingError(
            "Gemini не зміг відкрити це YouTube-відео. Обробку YouTube потрібно налаштувати "
            "(GEMINI_API_KEY)."
        )
    return UserFacingError("Сервіс Gemini зараз недоступний. Спробуйте пізніше.")


class GeminiService:
    def __init__(self, settings: Settings):
        if settings.gemini_backend == "vertex":
            self._client = genai.Client(
                enterprise=True,
                project=settings.google_cloud_project,
                location=settings.google_cloud_location,
            )
        else:
            self._client = genai.Client(api_key=settings.gemini_api_key)
        # Vertex AI rejects YouTube URLs (401) for projects like ours, while the Gemini
        # Developer API supports them, so YouTube goes through an AI Studio key when one is set.
        if settings.gemini_api_key and settings.gemini_backend == "vertex":
            self._youtube_client = genai.Client(api_key=settings.gemini_api_key)
        else:
            self._youtube_client = self._client
        self._models = [settings.gemini_model, *settings.gemini_fallback_models]
        self._system_instruction = prompts.SYSTEM_INSTRUCTION.format(language=settings.output_language)
        self._max_chars = settings.max_transcript_chars

    async def summarize(self, transcript: str, *, brief: bool = False) -> str:
        template = prompts.BRIEF_SUMMARY_PROMPT if brief else prompts.SUMMARY_PROMPT
        prompt = template.format(transcript=self._fit(transcript))
        response = await self._generate(prompt, temperature=0.3)
        return self._text(response)

    async def make_quiz(self, transcript: str, count: int) -> list[QuizQuestion]:
        prompt = prompts.QUIZ_PROMPT.format(count=count, transcript=self._fit(transcript))
        response = await self._generate(
            prompt,
            temperature=0.5,
            response_mime_type="application/json",
            response_schema=list[QuizQuestion],
        )
        try:
            questions = response.parsed or _QUIZ_ADAPTER.validate_json(response.text or "")
        except ValidationError as exc:
            logger.warning("Gemini returned an invalid quiz: %s", exc)
            raise UserFacingError("Не вдалося сформувати тест. Спробуйте ще раз.") from exc
        questions = sanitize_quiz(questions)
        if not questions:
            raise UserFacingError("Не вдалося сформувати тест. Спробуйте ще раз.")
        return questions[:count]

    async def answer(self, transcript: str, question: str) -> str:
        prompt = prompts.ANSWER_PROMPT.format(question=question, transcript=self._fit(transcript))
        response = await self._generate(prompt, temperature=0.2)
        return self._text(response)

    async def transcribe_youtube(self, url: str) -> str:
        """Gemini reads a public YouTube video by URL; nothing is downloaded by the bot."""
        contents = [
            types.Part.from_uri(file_uri=url, mime_type="video/mp4"),
            prompts.YOUTUBE_TRANSCRIPT_PROMPT,
        ]
        response = await self._generate(
            contents,
            youtube=True,
            temperature=0.0,
            # Low resolution is enough for a lecture and uses ~3x fewer tokens.
            media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW,
        )
        transcript = (response.text or "").strip()
        if not transcript:
            finish_reason = response.candidates[0].finish_reason if response.candidates else None
            logger.warning("Gemini returned no text for %s (finish_reason=%s)", url, finish_reason)
            if finish_reason == types.FinishReason.RECITATION:
                raise UserFacingError(
                    "Gemini відмовився обробляти це відео через захист авторського вмісту. "
                    "Спробуйте інше відео або надішліть аудіо лекції."
                )
            raise UserFacingError("У відео не вдалося знайти мовлення.")
        return transcript

    async def _generate(self, contents, *, youtube: bool = False, **config):
        client = self._youtube_client if youtube else self._client
        for model in self._models:
            try:
                return await client.aio.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=self._system_instruction, **config),
                )
            except genai_errors.APIError as exc:
                # The SDK has already retried; an overloaded or rate-limited model may
                # still work as the next one in the list, which has its own capacity and quota.
                if exc.code in _TRY_NEXT_MODEL_CODES and model != self._models[-1]:
                    logger.warning("Gemini model %s failed with %s, trying the next one", model, exc.code)
                    continue
                raise _user_facing_error(exc, youtube=youtube) from exc

    def _fit(self, transcript: str) -> str:
        return transcript[: self._max_chars]

    @staticmethod
    def _text(response) -> str:
        text = (response.text or "").strip()
        if not text:
            raise UserFacingError("Gemini повернув порожню відповідь. Спробуйте ще раз.")
        return text
