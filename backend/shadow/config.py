import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv() -> None:
    """Read KEY=VALUE lines from the project's .env (gitignored). Real env vars win."""
    for env in (Path(__file__).resolve().parents[2] / ".env", Path(__file__).resolve().parents[1] / ".env"):
        if not env.exists():
            continue
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default_factory=lambda: os.environ.get("MODEL_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.environ.get("SHADOW_BASE_URL", "https://api.meta.ai/v1"))
    # Narration matters: spark-1.3 audio is "not fully supported" per the docs, so default to 1.2.
    timeline_model: str = field(default_factory=lambda: os.environ.get("SHADOW_TIMELINE_MODEL", "muse-spark-1.2"))
    playbook_model: str = field(default_factory=lambda: os.environ.get("SHADOW_PLAYBOOK_MODEL", "muse-wonder-1.0"))
    # 0 = send the whole video in one call; N = slice into N-second windows (timestamps correct by construction).
    window_seconds: int = field(default_factory=lambda: _int("SHADOW_WINDOW_SECONDS", 0))
    # Reasoning shares the output budget; below ~4000 responses can come back empty.
    max_output_tokens: int = field(default_factory=lambda: max(4000, _int("SHADOW_MAX_OUTPUT_TOKENS", 12000)))
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("SHADOW_DATA_DIR", Path(__file__).resolve().parents[1] / "data")))
    # Seconds of slack when matching a step to timeline evidence.
    evidence_slack: float = field(default_factory=lambda: float(os.environ.get("SHADOW_EVIDENCE_SLACK", "4")))

    # Open-weights mode: Muse Spark Open on any OpenAI-compatible host.
    # Baseten: https://inference.baseten.co/v1 with model meta-models/muse-spark-open
    open_base_url: str = field(default_factory=lambda: os.environ.get("SHADOW_OPEN_BASE_URL", ""))
    open_api_key: str = field(default_factory=lambda: os.environ.get("SHADOW_OPEN_API_KEY", ""))
    open_model: str = field(default_factory=lambda: os.environ.get("SHADOW_OPEN_MODEL", "meta-models/muse-spark-open"))
    open_window_seconds: int = field(default_factory=lambda: _int("SHADOW_OPEN_WINDOW_SECONDS", 30))
    transcribe_model: str = field(default_factory=lambda: os.environ.get("SHADOW_TRANSCRIBE_MODEL", "muse-voice-transcribe-1.0"))
    locate_model: str = field(default_factory=lambda: os.environ.get("SHADOW_LOCATE_MODEL", "muse-spark-1.3"))
    sam_model: str = field(default_factory=lambda: os.environ.get("SHADOW_SAM_MODEL", "sam-3.1"))
    # Optional extras that call Meta APIs (need MODEL_API_KEY). "0" turns them off.
    use_transcribe: bool = field(default_factory=lambda: os.environ.get("SHADOW_TRANSCRIBE", "1") != "0")
    use_pointer: bool = field(default_factory=lambda: os.environ.get("SHADOW_POINTER", "1") != "0")

    # Public deploy guards: the upload endpoint spends real API money.
    max_upload_mb: int = field(default_factory=lambda: _int("SHADOW_MAX_UPLOAD_MB", 200))
    max_jobs: int = field(default_factory=lambda: _int("SHADOW_MAX_JOBS", 25))

    @property
    def live(self) -> bool:
        return bool(self.api_key)


settings = Settings()
