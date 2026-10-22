"""Structured output models for Gemini and their validation against Telegram limits."""

from pydantic import BaseModel

from bot.text_utils import clip

# Telegram quiz poll limits (https://core.telegram.org/bots/api#sendpoll).
POLL_QUESTION_LIMIT = 300
POLL_OPTION_LIMIT = 100
POLL_EXPLANATION_LIMIT = 200
POLL_MAX_OPTIONS = 10


class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    correct_index: int
    explanation: str


def sanitize_quiz(questions: list[QuizQuestion]) -> list[QuizQuestion]:
    """Drop malformed questions and trim the rest to fit Telegram quiz polls."""
    valid = []
    for item in questions:
        options = [option.strip() for option in item.options]
        if not item.question.strip() or any(not option for option in options):
            continue
        if not 2 <= len(options) <= POLL_MAX_OPTIONS:
            continue
        if not 0 <= item.correct_index < len(options):
            continue
        valid.append(
            QuizQuestion(
                # Leave room for the "N. " prefix added when the poll is sent.
                question=clip(item.question, POLL_QUESTION_LIMIT - 5),
                options=[clip(option, POLL_OPTION_LIMIT) for option in options],
                correct_index=item.correct_index,
                explanation=clip(item.explanation, POLL_EXPLANATION_LIMIT),
            )
        )
    return valid
