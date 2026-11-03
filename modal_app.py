"""Deploy Shadow (API + built UI) to Modal.

One-time setup (PowerShell, from this folder):
    pip install modal
    modal setup                                   # opens the browser to link your Modal account
    modal secret create shadow-secrets MODEL_API_KEY=<meta key> SHADOW_WINDOW_SECONDS=0
    #   optional open-weights mode (Baseten example):
    #   SHADOW_OPEN_BASE_URL=https://inference.baseten.co/v1 SHADOW_OPEN_API_KEY=<baseten key>
Every deploy:
    cd frontend; npm run build; cd ..
    modal deploy modal_app.py                     # prints the public URL
"""
from pathlib import Path

import modal

ROOT = Path(__file__).parent

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install_from_requirements(str(ROOT / "backend" / "requirements.txt"))
    .env({"SHADOW_DATA_DIR": "/data",
          # open-weights mode: Muse Spark Open on Nebius Token Factory (the key is in the shadow-secrets secret)
          "SHADOW_OPEN_BASE_URL": "https://api.tokenfactory.nebius.com/v1",
          "SHADOW_OPEN_MODEL": "meta-models/muse-spark-open"})
    .add_local_dir(str(ROOT / "backend"), "/app/backend", ignore=["data", "tests", "**/__pycache__", ".venv"])
    .add_local_dir(str(ROOT / "frontend" / "dist"), "/app/frontend/dist")
)

app = modal.App("shadow")
data = modal.Volume.from_name("shadow-data", create_if_missing=True)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("shadow-secrets")],
    volumes={"/data": data},
    timeout=1800,
    max_containers=1,          # jobs run in background threads and share one on-disk store
    scaledown_window=900,      # keep the container alive while a job finishes
)
@modal.concurrent(max_inputs=32)
@modal.asgi_app()
def web():
    import sys

    sys.path.insert(0, "/app/backend")
    from shadow.api import app as fastapi_app

    return fastapi_app
