"""ffmpeg helpers: duration, fixed windows, single frames."""
import json
import shutil
import subprocess
from pathlib import Path


def _need(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise RuntimeError(f"{tool} not found on PATH (install ffmpeg)")
    return path


def duration(path: Path) -> float:
    out = subprocess.run(
        [_need("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def slice_windows(path: Path, out_dir: Path, window: int, total: float) -> list[tuple[float, Path]]:
    """Cut the video into `window`-second MP4 clips. Re-encodes so cuts land exactly on the offsets."""
    out_dir.mkdir(parents=True, exist_ok=True)
    clips = []
    start = 0.0
    i = 0
    while start < total - 0.5:
        clip = out_dir / f"window_{i:03d}.mp4"
        subprocess.run(
            [_need("ffmpeg"), "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-i", str(path),
             "-t", str(window), "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
             "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(clip)],
            check=True,
        )
        clips.append((start, clip))
        start += window
        i += 1
    return clips


def frame_at(path: Path, t: float, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [_need("ffmpeg"), "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(path),
         "-frames:v", "1", "-q:v", "3", str(out)],
        check=True,
    )
    return out


def has_audio(path: Path) -> bool:
    out = subprocess.run(
        [_need("ffprobe"), "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    ).stdout.strip()
    return bool(out)


def extract_wav(path: Path, out: Path, rate: int = 24000):
    """Mono 16-bit PCM WAV (what Muse Voice Transcribe expects). Returns None if the video has no audio."""
    if not has_audio(path):
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [_need("ffmpeg"), "-y", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(rate),
         "-c:a", "pcm_s16le", "-map_metadata", "-1", str(out)],
        check=True,
    )
    return out


def frame_size(path: Path) -> tuple[int, int]:
    out = subprocess.run(
        [_need("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip().split(",")
    return int(out[0]), int(out[1])
