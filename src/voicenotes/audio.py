"""Audio decoding (via ffmpeg) and silence-aware chunking."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16_000


class AudioError(RuntimeError):
    pass


def ffmpeg_path() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise AudioError("ffmpeg not found. Install it with: brew install ffmpeg")
    return exe


def load_audio(path: str | Path, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Decode any audio/video file (m4a, mp3, webm, wav, ...) to mono float32 at `sr`."""
    path = Path(path)
    if not path.exists():
        raise AudioError(f"audio file not found: {path}")
    cmd = [ffmpeg_path(), "-nostdin", "-loglevel", "error", "-i", str(path),
           "-f", "s16le", "-ac", "1", "-ar", str(sr), "-"]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise AudioError(f"ffmpeg failed to decode {path.name}: {proc.stderr.decode(errors='ignore').strip()}")
    return np.frombuffer(proc.stdout, np.int16).astype(np.float32) / 32768.0


def duration_seconds(samples: np.ndarray, sr: int = SAMPLE_RATE) -> float:
    return len(samples) / sr


def split_on_silence(
    samples: np.ndarray,
    sr: int = SAMPLE_RATE,
    max_chunk_s: float = 28.0,
    min_chunk_s: float = 5.0,
    frame_s: float = 0.03,
) -> list[tuple[int, int]]:
    """Split audio into chunks of at most `max_chunk_s`, cutting at the quietest
    frame found between `min_chunk_s` and `max_chunk_s` of each chunk.

    Returns (start_sample, end_sample) pairs covering the whole signal.
    Whisper only sees 30 s at a time, so backends without their own long-form
    handling use this.
    """
    n = len(samples)
    if n == 0:
        return []
    max_len, min_len = int(max_chunk_s * sr), int(min_chunk_s * sr)
    frame = max(1, int(frame_s * sr))
    chunks: list[tuple[int, int]] = []
    start = 0
    while n - start > max_len:
        lo, hi = start + min_len, start + max_len
        window = samples[lo:hi]
        nframes = len(window) // frame
        energy = np.sqrt(np.mean(window[: nframes * frame].reshape(nframes, frame) ** 2, axis=1))
        cut = lo + int(np.argmin(energy)) * frame + frame // 2
        chunks.append((start, cut))
        start = cut
    chunks.append((start, n))
    return chunks


def is_silent(samples: np.ndarray, threshold: float = 1e-3) -> bool:
    return samples.size == 0 or float(np.sqrt(np.mean(samples**2))) < threshold
