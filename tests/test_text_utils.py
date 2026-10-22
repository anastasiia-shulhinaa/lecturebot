from bot.text_utils import clip, format_duration, html_to_plain, markdown_to_telegram_html, split_text


def test_clip():
    assert clip("  short  ", 10) == "short"
    assert clip("a" * 20, 10) == "a" * 9 + "…"
    assert len(clip("a" * 20, 10)) == 10


def test_split_text_respects_limit_and_keeps_content():
    text = "\n".join(f"Рядок номер {i}" for i in range(500))
    chunks = split_text(text, limit=200)
    assert all(len(chunk) <= 200 for chunk in chunks)
    assert "\n".join(chunks) == text


def test_split_text_hard_splits_long_line():
    chunks = split_text("x" * 450, limit=200)
    assert [len(chunk) for chunk in chunks] == [200, 200, 50]


def test_split_text_short():
    assert split_text("hello") == ["hello"]
    assert split_text("") == []


def test_markdown_to_telegram_html():
    markdown = "## Тема **лекції**\n- **Хмара** — модель <доступу>\n* пункт з `кодом`"
    assert markdown_to_telegram_html(markdown) == (
        "<b>Тема лекції</b>\n"
        "• <b>Хмара</b> — модель &lt;доступу&gt;\n"
        "• пункт з <code>кодом</code>"
    )


def test_html_to_plain():
    assert html_to_plain("<b>A</b> &lt;b&gt;") == "A <b>"


def test_format_duration():
    assert format_duration(5) == "0:05"
    assert format_duration(750) == "12:30"
    assert format_duration(3723) == "1:02:03"
