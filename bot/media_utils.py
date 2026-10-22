"""FFmpeg helpers: convert any audio/video to mono 16 kHz FLAC and measure its length."""

import shutil
import subprocess
from pathlib import Path

from bot.errors import UserFacingError

SAMPLE_RATE_HZ = 16_000


def ensure_ffmpeg() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise RuntimeError(
            f"{', '.join(missing)} not found in PATH. Install FFmpeg "
            "(Windows: winget install Gyan.FFmpeg) and restart the terminal."
        )


def convert_to_flac(source: Path, target: Path) -> None:
    """Extract the audio track and convert it to the format Speech-to-Text expects."""
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(source),
        "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE_HZ), "-c:a", "flac",
        str(target),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not target.exists() or target.stat().st_size == 0:
        raise UserFacingError(
            "Не вдалося прочитати аудіо з файлу. Перевірте, що файл не пошкоджений "
            "і містить звукову доріжку."
        )


def probe_duration(path: Path) -> float:
    command = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise UserFacingError("Не вдалося визначити тривалість запису.") from exc
