import tempfile
from pathlib import Path
from config import Config
from transcription.vocab import get_vocab

# Use faster-whisper (more reliable than mlx-whisper)
from faster_whisper import WhisperModel

_whisper_model = None


def _infer_audio_ext(content_type: str) -> str:
    """Infer audio file extension from Content-Type header."""
    ext_map = {
        "audio/mp4": ".m4a",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/webm": ".webm",
    }
    return ext_map.get(content_type, ".m4a")


async def transcribe_audio(audio_bytes: bytes, content_type: str = "audio/mp4") -> str:
    """Transcribe audio file using Whisper. Return transcribed text."""
    ext = _infer_audio_ext(content_type)
    vocab = get_vocab()

    temp_file = None
    try:
        # Write bytes to temp file
        temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        temp_file.write(audio_bytes)
        temp_file.close()

        global _whisper_model
        if _whisper_model is None:
            _whisper_model = WhisperModel(
                "base",
                device="cpu",
                compute_type="int8",
            )

        segments, _ = _whisper_model.transcribe(
            temp_file.name,
            language=Config.WHISPER_LANGUAGE,
            initial_prompt=vocab,
        )
        result = "".join(s.text for s in segments)

        return result.strip()

    finally:
        if temp_file:
            Path(temp_file.name).unlink(missing_ok=True)
