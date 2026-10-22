"""Google Cloud Speech-to-Text: turns a FLAC file into a transcript."""

import logging
import uuid
from pathlib import Path

from google.api_core import exceptions as google_exceptions
from google.cloud import speech

from bot.errors import UserFacingError
from bot.media_utils import SAMPLE_RATE_HZ
from bot.storage import AudioStorage

logger = logging.getLogger(__name__)

# Synchronous recognition accepts at most 1 minute / 10 MB of inline audio.
SYNC_MAX_SECONDS = 55
SYNC_MAX_BYTES = 10 * 1024 * 1024


class SpeechTranscriber:
    def __init__(self, storage: AudioStorage, language: str, alt_languages: list[str]):
        self._client = speech.SpeechClient()
        self._storage = storage
        self._config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
            sample_rate_hertz=SAMPLE_RATE_HZ,
            audio_channel_count=1,
            language_code=language,
            alternative_language_codes=alt_languages,
            enable_automatic_punctuation=True,
        )

    def transcribe(self, flac_path: Path, duration_seconds: float) -> str:
        """Blocking call: run it in a worker thread."""
        try:
            if duration_seconds <= SYNC_MAX_SECONDS and flac_path.stat().st_size <= SYNC_MAX_BYTES:
                response = self._client.recognize(
                    config=self._config,
                    audio=speech.RecognitionAudio(content=flac_path.read_bytes()),
                )
            else:
                response = self._recognize_long(flac_path, duration_seconds)
        except google_exceptions.ResourceExhausted as exc:
            raise UserFacingError("Вичерпано квоту Speech-to-Text. Спробуйте пізніше.") from exc
        except google_exceptions.GoogleAPICallError as exc:
            logger.exception("Speech-to-Text request failed")
            raise UserFacingError("Сервіс розпізнавання мовлення зараз недоступний.") from exc

        transcript = " ".join(
            result.alternatives[0].transcript.strip()
            for result in response.results
            if result.alternatives
        ).strip()
        if not transcript:
            raise UserFacingError(
                "Мовлення не розпізнано. Можливо, у записі тиша, музика або дуже шумний звук."
            )
        return transcript

    def _recognize_long(self, flac_path: Path, duration_seconds: float):
        blob_name = f"audio/{uuid.uuid4().hex}.flac"
        uri = self._storage.upload(flac_path, blob_name)
        try:
            operation = self._client.long_running_recognize(
                config=self._config, audio=speech.RecognitionAudio(uri=uri)
            )
            # Recognition is usually much faster than real time; this is a safety cap.
            return operation.result(timeout=int(duration_seconds) + 600)
        finally:
            try:
                self._storage.delete(blob_name)
            except google_exceptions.GoogleAPICallError:
                logger.warning("Could not delete %s; the lifecycle rule will remove it", blob_name)
