"""YouTube Data API v3: find a video in a message and fetch its metadata."""

import logging
import re
from dataclasses import dataclass

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from bot.errors import UserFacingError

logger = logging.getLogger(__name__)

_VIDEO_ID_RE = re.compile(
    r"(?:https?://)?(?:www\.|m\.|music\.)?"
    r"(?:youtube\.com/(?:watch\?(?:[^\s#]*&)?v=|shorts/|live/|embed/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])"
)
_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def extract_video_id(text: str) -> str | None:
    match = _VIDEO_ID_RE.search(text)
    return match.group(1) if match else None


def parse_iso8601_duration(value: str) -> int:
    """Convert a YouTube duration such as 'PT1H2M3S' into seconds."""
    match = _DURATION_RE.match(value)
    if not match:
        raise ValueError(f"Unsupported duration: {value!r}")
    parts = {name: int(number or 0) for name, number in match.groupdict().items()}
    return parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]


@dataclass(frozen=True)
class VideoInfo:
    video_id: str
    title: str
    channel: str
    duration_seconds: int
    privacy_status: str
    is_live: bool

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


class YouTubeService:
    def __init__(self, api_key: str):
        self._youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)

    def get_video(self, video_id: str) -> VideoInfo | None:
        """Blocking call: run it in a worker thread. Costs 1 unit of the daily quota."""
        try:
            response = (
                self._youtube.videos()
                .list(part="snippet,contentDetails,status", id=video_id)
                .execute()
            )
        except HttpError as exc:
            logger.exception("YouTube Data API request failed")
            raise UserFacingError("Не вдалося отримати дані відео з YouTube.") from exc

        items = response.get("items", [])
        if not items:
            return None
        item = items[0]
        return VideoInfo(
            video_id=video_id,
            title=item["snippet"]["title"],
            channel=item["snippet"]["channelTitle"],
            duration_seconds=parse_iso8601_duration(item["contentDetails"]["duration"]),
            privacy_status=item["status"]["privacyStatus"],
            is_live=item["snippet"].get("liveBroadcastContent", "none") != "none",
        )
