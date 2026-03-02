# 2025-02-26
"""Radio comms APIs – test + audio proxy + incident lines."""

from pathlib import Path

from flask import Blueprint, send_file, request

from extensions import socketio
from services.tts_service import get_audio_path

radio_bp = Blueprint("radio", __name__, url_prefix="/api/radio")

_STATIC_AUDIO_DIR = Path(__file__).resolve().parents[1] / "audio"
_STATIC_FILES = {
    "controller": _STATIC_AUDIO_DIR / "Controller_Radio.mp3",
    "dispatch": _STATIC_AUDIO_DIR / "Dispatch_Radio.mp3",
}


@radio_bp.get("/static/<name>")
def serve_static_audio(name: str):
    """Serve static radio clips: controller or dispatch."""
    key = name.lower().rstrip(".mp3")
    if key not in _STATIC_FILES:
        return {"error": "Not found"}, 404
    path = _STATIC_FILES[key]
    if not path.is_file():
        return {"error": "File not found"}, 404
    return send_file(path, mimetype="audio/mpeg", as_attachment=False)


@radio_bp.get("/test")
def test_emit():
    """Emit a simple radio_comm. Use to verify frontend receives it."""
    socketio.emit(
        "radio_comm",
        {"role": "control", "text": "Test. Control to unit one, respond to test incident in grid A."},
    )
    return {"ok": True, "message": "Emitted test radio_comm"}


@radio_bp.get("/audio/<filename>")
def serve_audio(filename: str):
    """Serve a generated radio TTS WAV file."""
    if ".." in filename or "/" in filename:
        return {"error": "Invalid filename"}, 400
    path = get_audio_path(filename)
    if not path:
        return {"error": "File not found"}, 404
    return send_file(path, mimetype="audio/wav", as_attachment=False)


@radio_bp.post("/incident-line")
def incident_line():
    """
    Generate a single radio line for an incident and return audio filename.
    Used by the frontend after a vehicle is dispatched.
    """
    data = request.get_json(silent=True) or {}
    role = (data.get("role") or "control").strip().lower()
    vehicle_id = data.get("vehicle_id")
    incident_type = (data.get("incident_type") or "incident").replace("_", " ")
    hex_label = data.get("hex_label")
    hex_id = data.get("hex_id")
    if not hex_label and hex_id:
        try:
            from utils.hex_labels import get_hex_label
            hex_label = get_hex_label(str(hex_id))
        except Exception:
            hex_label = "the area"
    hex_label = hex_label or "the area"

    if not vehicle_id:
        return {"error": "vehicle_id required"}, 400

    if role == "dispatch":
        text = f"Dispatch {vehicle_id} to control, en route to hex {hex_label}."
        speaker_idx = 1
    else:
        text = f"Control to {vehicle_id}, respond to {incident_type} in hex {hex_label}."
        speaker_idx = 0

    try:
        from services.tts_service import synthesize
        from services.radio_fx import apply_radio_fx
        from pathlib import Path
        import tempfile

        wav_path = synthesize(text, speaker_idx=speaker_idx)
        if not wav_path:
            # TTS disabled – let frontend fall back to browser voice.
            return {"audio_filename": None, "text": text}, 200

        out_name = f"radio_fx_{Path(wav_path).name}"
        out_dir = Path(tempfile.gettempdir()) / "civic1_radio"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / out_name
        apply_radio_fx(wav_path, str(out_path))

        return {
            "audio_filename": out_path.name,
            "text": text,
        }, 200
    except Exception as exc:  # pragma: no cover - best-effort fallback
        return {"error": str(exc), "text": text, "audio_filename": None}, 200
