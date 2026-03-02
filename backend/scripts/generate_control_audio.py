#!/usr/bin/env python3
# 2025-02-26
"""
Generate control radio audio: "Control to 53, respond to medical emergency in grid Y-1"
Uses Controller_Radio.mp3 as voice sample (voice cloning via Coqui XTTS).
Saves to backend/audio/Control_53_medical_Y1.wav
Run from backend dir: python scripts/generate_control_audio.py
"""
import os
import subprocess
import sys
from pathlib import Path

# Ensure we run from backend dir
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

# Enable TTS and use XTTS for voice cloning
os.environ["ENABLE_RADIO_TTS"] = "true"
os.environ["RADIO_TTS_MODEL"] = "tts_models/multilingual/multi-dataset/xtts_v2"
os.environ["RADIO_TTS_LANGUAGE"] = "en"

TEXT = "Control to 53, respond to medical emergency in grid Y-1"
OUTPUT_NAME = "Control_53_medical_Y1"
AUDIO_DIR = BACKEND_DIR / "audio"
SAMPLE_PATH = AUDIO_DIR / "Controller_Radio.mp3"
OUTPUT_WAV = AUDIO_DIR / f"{OUTPUT_NAME}.wav"
OUTPUT_MP3 = AUDIO_DIR / f"{OUTPUT_NAME}.mp3"


def coerce_to_wav(mp3_path: Path) -> Path:
    """Convert MP3 to mono 16k WAV for XTTS."""
    wav_path = AUDIO_DIR / f"speaker_{mp3_path.stem}.wav"
    if wav_path.exists() and wav_path.stat().st_mtime >= mp3_path.stat().st_mtime:
        return wav_path
    cmd = ["ffmpeg", "-y", "-i", str(mp3_path), "-ac", "1", "-ar", "16000", str(wav_path)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return wav_path


def main():
    if not SAMPLE_PATH.exists():
        print(f"Error: Sample not found: {SAMPLE_PATH}")
        sys.exit(1)

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    # Try Coqui XTTS (voice cloning from Controller_Radio.mp3)
    try:
        import torch
        from TTS.api import TTS

        print("Loading Coqui XTTS (first run may download model ~1.8GB)...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

        speaker_wav = coerce_to_wav(SAMPLE_PATH)
        print(f"Voice sample: {speaker_wav}")

        print(f"Synthesizing: {TEXT}")
        tts.tts_to_file(
            text=TEXT,
            speaker_wav=str(speaker_wav),
            language="en",
            file_path=str(OUTPUT_WAV),
        )
        print(f"Saved: {OUTPUT_WAV}")

    except ImportError:
        print("Coqui TTS not installed. Using gTTS fallback (generic voice, not cloned).")
        print("For voice cloning, install: pip install coqui-tts torch")
        try:
            from gtts import gTTS
            tts = gTTS(text=TEXT, lang="en", slow=False)
            tts.save(str(OUTPUT_MP3))
            print(f"Saved: {OUTPUT_MP3}")
        except ImportError:
            print("Install gTTS: pip install gtts")
            sys.exit(1)

    # Convert WAV to MP3 if we have WAV
    if OUTPUT_WAV.exists() and subprocess.run(["which", "ffmpeg"], capture_output=True).returncode == 0:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(OUTPUT_WAV), "-q:a", "4", str(OUTPUT_MP3)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"Saved: {OUTPUT_MP3}")

    out = OUTPUT_MP3 if OUTPUT_MP3.exists() else OUTPUT_WAV
    print(f"Done. Play with: ffplay {out}")


if __name__ == "__main__":
    main()
