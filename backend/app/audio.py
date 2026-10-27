import hashlib
import wave
from pathlib import Path
from .providers import ProcessingError

AUDIO_TYPES = {"audio/webm", "video/webm", "audio/mp4", "video/mp4", "audio/mpeg", "audio/wav", "audio/x-wav",
               "audio/ogg", "application/ogg", "audio/flac", "audio/x-m4a", "audio/aac", "application/octet-stream"}


def file_sha(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def normalize_audio(source: Path, destination: Path, max_seconds: int):
    """Decode any supported input into bounded, mono 16kHz PCM16 WAV; never trust client duration."""
    try:
        import av
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        total, energy = 0, 0.0
        with av.open(str(source)) as container, wave.open(str(destination), "wb") as out:
            if not container.streams.audio:
                raise ProcessingError("INVALID_AUDIO", "The upload has no audio track.", False)
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(16000)
            for frame in container.decode(audio=0):
                for pcm in resampler.resample(frame):
                    samples = pcm.to_ndarray().reshape(-1)
                    total += len(samples)
                    if total > max_seconds * 16000:
                        raise ProcessingError("DURATION_LIMIT", f"Audio exceeds {max_seconds} seconds.", False)
                    energy += float((samples.astype("float64") ** 2).sum())
                    out.writeframes(samples.tobytes())
            for pcm in resampler.resample(None):
                samples = pcm.to_ndarray().reshape(-1)
                total += len(samples)
                if total > max_seconds * 16000:
                    raise ProcessingError("DURATION_LIMIT", "Decoded audio exceeds the duration limit.", False)
                energy += float((samples.astype("float64") ** 2).sum())
                out.writeframes(samples.tobytes())
            if total < 1600:
                raise ProcessingError("EMPTY_AUDIO", "Record at least a tenth of a second of speech.", False)
            if (energy / total) ** 0.5 < 12:
                raise ProcessingError("NO_SPEECH", "The recording is silent or too quiet.", False)
        return total / 16000
    except ProcessingError:
        destination.unlink(missing_ok=True)
        raise
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise ProcessingError("INVALID_AUDIO", "Audio could not be decoded. Upload WAV, WebM, MP4/M4A, MP3, FLAC or Ogg.", False) from exc
