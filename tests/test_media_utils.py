import shutil
import subprocess

import pytest

from bot.errors import UserFacingError
from bot.media_utils import convert_to_flac, probe_duration

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg is not installed")


def test_convert_video_to_flac(tmp_path):
    video = tmp_path / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=black:s=160x120:d=3",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
            "-shortest", str(video),
        ],
        check=True,
    )
    flac = tmp_path / "audio.flac"
    convert_to_flac(video, flac)
    assert flac.stat().st_size > 0
    assert probe_duration(flac) == pytest.approx(3, abs=0.2)


def test_convert_broken_file(tmp_path):
    broken = tmp_path / "broken.mp3"
    broken.write_bytes(b"not really audio")
    with pytest.raises(UserFacingError):
        convert_to_flac(broken, tmp_path / "out.flac")
