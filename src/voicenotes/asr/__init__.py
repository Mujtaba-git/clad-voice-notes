"""Speech recognition backends (all run Whisper locally)."""
from .base import Transcriber, normalize_language, clean_segments
from .factory import available_backends, create_transcriber

__all__ = ["Transcriber", "normalize_language", "clean_segments", "available_backends", "create_transcriber"]
