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
        self._model = settings.gemini_model
        self._system_instruction = prompts.SYSTEM_INSTRUCTION.format(language=settings.output_language)
        self._max_chars = settings.max_transcript_chars

    async def summarize(self, transcript: str) -> str:
        prompt = prompts.SUMMARY_PROMPT.format(transcript=self._fit(transcript))
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
            temperature=0.0,
            # Low resolution is enough for a lecture and uses ~3x fewer tokens.
            media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW,
        )
        transcript = (response.text or "").strip()
        if not transcript:
            raise UserFacingError("У відео не вдалося знайти мовлення.")
        return transcript

    async def _generate(self, contents, **config):
        try:
            return await self._client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=self._system_instruction, **config),
            )
        except genai_errors.APIError as exc:
            logger.exception("Gemini request failed")
            if exc.code == 429:
                raise UserFacingError("Вичерпано квоту Gemini. Спробуйте за хвилину.") from exc
            raise UserFacingError("Сервіс Gemini зараз недоступний. Спробуйте пізніше.") from exc

    def _fit(self, transcript: str) -> str:
        return transcript[: self._max_chars]

    @staticmethod
    def _text(response) -> str:
        text = (response.text or "").strip()
        if not text:
            raise UserFacingError("Gemini повернув порожню відповідь. Спробуйте ще раз.")
        return text
