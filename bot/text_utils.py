"""Text helpers for Telegram: length limits, Markdown -> Telegram HTML, durations."""

import html
import re

TELEGRAM_MESSAGE_LIMIT = 4096

_HEADING_RE = re.compile(r"^\s*#{1,6}\s+(.*)$")
_BULLET_RE = re.compile(r"^(\s*)[-*+]\s+")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_CODE_RE = re.compile(r"`([^`]+)`")
_TAG_RE = re.compile(r"<[^>]+>")


def clip(text: str, limit: int) -> str:
    """Trim text to `limit` characters, marking the cut with an ellipsis."""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def split_text(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Split text into chunks of at most `limit` characters, preferring line breaks."""
    chunks: list[str] = []
    current = ""
    for line in text.splitlines():
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current.strip():
        chunks.append(current)
    return [chunk for chunk in chunks if chunk.strip()]


def markdown_to_telegram_html(markdown: str) -> str:
    """Convert the simple Markdown Gemini produces into Telegram-safe HTML.

    Every tag opens and closes on the same line, so the result can be split by lines.
    """
    lines = []
    for line in markdown.splitlines():
        escaped = html.escape(line, quote=False)
        heading = _HEADING_RE.match(escaped)
        if heading:
            escaped = f"<b>{heading.group(1).replace('**', '')}</b>"
        else:
            escaped = _BULLET_RE.sub(r"\1• ", escaped)
            escaped = _BOLD_RE.sub(r"<b>\1</b>", escaped)
            escaped = _CODE_RE.sub(r"<code>\1</code>", escaped)
        lines.append(escaped)
    return "\n".join(lines)


def html_to_plain(text: str) -> str:
    return html.unescape(_TAG_RE.sub("", text))


def format_duration(seconds: float) -> str:
    total = int(round(seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
