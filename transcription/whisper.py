import tempfile
from pathlib import Path
from config import Config
from transcription.vocab import get_vocab

# Try to import mlx-whisper; fallback to faster-whisper
try:
    import mlx_whisper
    _use_mlx = True
    _faster_whisper_model = None
except ImportError:
    _use_mlx = False
    from faster_whisper import WhisperModel
    _faster_whisper_model = None


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

        if _use_mlx:
            result = mlx_whisper.transcribe(
                temp_file.name,
                path_or_hf_repo=Config.WHISPER_MODEL,
                initial_prompt=vocab,
                language=Config.WHISPER_LANGUAGE,
            )
        else:
            global _faster_whisper_model
            if _faster_whisper_model is None:
                _faster_whisper_model = WhisperModel(
                    Config.WHISPER_MODEL.split("/")[-1],
                    device="cpu",
                    compute_type="int8",
                )

            segments, _ = _faster_whisper_model.transcribe(
                temp_file.name,
                language=Config.WHISPER_LANGUAGE,
                initial_prompt=vocab,
            )
            result = {"text": "".join(s.text for s in segments)}

        return result["text"].strip()

    finally:
        if temp_file:
            Path(temp_file.name).unlink(missing_ok=True)
