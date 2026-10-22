import pytest

from bot.youtube_service import extract_video_id, parse_iso8601_duration


@pytest.mark.parametrize(
    "text",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?feature=share&v=dQw4w9WgXcQ&t=42",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ?si=abc",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "Подивись лекцію youtube.com/watch?v=dQw4w9WgXcQ будь ласка",
    ],
)
def test_extract_video_id(text):
    assert extract_video_id(text) == "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "text",
    [
        "просто текст",
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=short",
    ],
)
def test_extract_video_id_none(text):
    assert extract_video_id(text) is None


@pytest.mark.parametrize(
    ("value", "seconds"),
    [
        ("PT45S", 45),
        ("PT12M30S", 750),
        ("PT1H2M3S", 3723),
        ("PT2H", 7200),
        ("P1DT1S", 86401),
        ("P0D", 0),
    ],
)
def test_parse_iso8601_duration(value, seconds):
    assert parse_iso8601_duration(value) == seconds


def test_parse_iso8601_duration_invalid():
    with pytest.raises(ValueError):
        parse_iso8601_duration("12:30")
