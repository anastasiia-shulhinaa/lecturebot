"""Google Cloud Storage: temporary home for long audio files during transcription."""

from pathlib import Path

from google.cloud import storage


class AudioStorage:
    def __init__(self, project: str | None, bucket_name: str):
        self._bucket = storage.Client(project=project).bucket(bucket_name)

    def upload(self, path: Path, blob_name: str) -> str:
        """Upload a file and return its gs:// URI."""
        blob = self._bucket.blob(blob_name)
        blob.upload_from_filename(str(path), content_type="audio/flac")
        return f"gs://{self._bucket.name}/{blob_name}"

    def delete(self, blob_name: str) -> None:
        # The bucket's lifecycle rule removes leftovers after a day anyway.
        self._bucket.blob(blob_name).delete()
