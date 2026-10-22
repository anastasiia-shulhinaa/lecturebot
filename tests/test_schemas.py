from bot.schemas import POLL_EXPLANATION_LIMIT, POLL_OPTION_LIMIT, QuizQuestion, sanitize_quiz


def make(**overrides):
    data = {
        "question": "Що таке IaaS?",
        "options": ["Інфраструктура як сервіс", "Платформа", "ПЗ", "Мережа"],
        "correct_index": 0,
        "explanation": "IaaS надає обчислювальні ресурси.",
    }
    data.update(overrides)
    return QuizQuestion(**data)


def test_valid_question_is_kept():
    assert sanitize_quiz([make()]) == [make()]


def test_invalid_questions_are_dropped():
    questions = [
        make(correct_index=4),
        make(correct_index=-1),
        make(options=["Лише один"]),
        make(options=["A", " ", "C", "D"]),
        make(question="   "),
    ]
    assert sanitize_quiz(questions) == []


def test_long_texts_are_clipped():
    [question] = sanitize_quiz([make(options=["x" * 150, "B", "C", "D"], explanation="y" * 300)])
    assert len(question.options[0]) == POLL_OPTION_LIMIT
    assert len(question.explanation) == POLL_EXPLANATION_LIMIT
