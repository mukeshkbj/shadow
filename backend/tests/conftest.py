import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("SHADOW_DATA_DIR", tempfile.mkdtemp(prefix="shadow-test-"))
# Tests never use real keys: blank them so the project .env (loaded with setdefault) can't fill them.
for _k in ("MODEL_API_KEY", "SHADOW_OPEN_BASE_URL", "SHADOW_OPEN_API_KEY"):
    os.environ[_k] = ""
