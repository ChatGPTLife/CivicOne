# 2025-02-26
"""Coqui TTS service for radio comms. Generates speech from text."""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_TTS_INSTANCE = None
_AUDIO_DIR: Path | None = None
_TTS_MODEL_NAME: str | None = None


def _get_audio_dir() -> Path:
    global _AUDIO_DIR
    if _AUDIO_DIR is None:
        d = Path(tempfile.gettempdir()) / "civic1_radio"
        d.mkdir(parents=True, exist_ok=True)
        _AUDIO_DIR = d
    return _AUDIO_DIR


def get_audio_path(filename: str) -> Path | None:
    """Return full path to audio file if it exists."""
    path = _get_audio_dir() / filename
    return path if path.is_file() else None


def _default_ref_paths() -> tuple[str, str]:
    """Default bundled voice references (if present)."""
    backend_dir = Path(__file__).resolve().parents[1]
    control = backend_dir / "audio" / "Control_Radio.mp3"
    dispatch = backend_dir / "audio" / "Dispatch_Radio.mp3"
    return (str(control), str(dispatch))


def _coerce_to_wav(input_path: str) -> str:
    """
    Coqui XTTS speaker reference is best provided as mono 16k WAV.
    Converts using ffmpeg (required).
    """
    p = Path(input_path)
    if not p.exists():
        raise FileNotFoundError(input_path)
    if p.suffix.lower() == ".wav":
        return str(p)

    out_dir = _get_audio_dir()
    out_wav = out_dir / f"speaker_{p.stem}.wav"
    if out_wav.exists() and out_wav.stat().st_mtime >= p.stat().st_mtime:
        return str(out_wav)

    cmd = ["ffmpeg", "-y", "-i", str(p), "-ac", "1", "-ar", "16000", str(out_wav)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(out_wav)


def _ensure_tts():
    """Lazy-load TTS model (heavy on first import)."""
    global _TTS_INSTANCE, _TTS_MODEL_NAME
    if _TTS_INSTANCE is not None:
        return _TTS_INSTANCE
    try:
        import torch
        from TTS.api import TTS

        device = "cuda" if torch.cuda.is_available() else "cpu"
        # Override via env for best quality (recommended):
        # RADIO_TTS_MODEL=tts_models/multilingual/multi-dataset/xtts_v2
        model_name = os.getenv("RADIO_TTS_MODEL", "tts_models/en/vctk/vits")
        _TTS_MODEL_NAME = model_name
        tts = TTS(model_name).to(device)
        _TTS_INSTANCE = tts
        return tts
    except ImportError as e:
        logger.warning("Coqui TTS not installed: %s. Radio audio disabled.", e)
        return None


def synthesize(text: str, speaker_idx: int = 0, out_filename: str | None = None) -> str | None:
    """
    Synthesize speech from text. Returns path to generated WAV file, or None on failure.
    speaker_idx: 0 = control voice, 1 = dispatch voice
    """
    if not os.getenv("ENABLE_RADIO_TTS", "false").lower() in ("true", "1", "yes"):
        return None

    tts = _ensure_tts()
    if tts is None:
        return None

    try:
        audio_dir = _get_audio_dir()
        if out_filename is None:
            import time
            out_filename = f"radio_{int(time.time() * 1000)}.wav"
        out_path = audio_dir / out_filename

        # Voice reference (for XTTS voice cloning) - speaker 0=control, 1=dispatch.
        language = os.getenv("RADIO_TTS_LANGUAGE", "en")
        default_control, default_dispatch = _default_ref_paths()
        control_ref = os.getenv("RADIO_SPEAKER_WAV_CONTROL") or (default_control if Path(default_control).exists() else "")
        dispatch_ref = os.getenv("RADIO_SPEAKER_WAV_DISPATCH") or (default_dispatch if Path(default_dispatch).exists() else "")
        ref = control_ref if speaker_idx == 0 else dispatch_ref

        # Prefer speaker_wav when we have a ref; fall back to speaker_idx when model doesn't support it.
        if ref:
            speaker_wav = _coerce_to_wav(ref)
            try:
                tts.tts_to_file(
                    text=text,
                    speaker_wav=speaker_wav,
                    language=language,
                    file_path=str(out_path),
                )
            except TypeError:
                # e.g. vctk/vits doesn't accept speaker_wav
                tts.tts_to_file(text=text, speaker_idx=speaker_idx, file_path=str(out_path))
        else:
            tts.tts_to_file(text=text, speaker_idx=speaker_idx, file_path=str(out_path))

        return str(out_path)
    except Exception as e:
        logger.exception("TTS synthesis failed: %s", e)
        return None
