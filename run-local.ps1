# Run Shadow on this PC:   .\run-local.ps1      then open http://localhost:8000
# Reads MODEL_API_KEY from .env (copy .env.example) or from $env:MODEL_API_KEY.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path "backend\.venv")) { python -m venv backend\.venv }
& backend\.venv\Scripts\python.exe -m pip install --quiet -r backend\requirements.txt
Push-Location frontend; npm install --silent; npm run build; Pop-Location
Push-Location backend
& .venv\Scripts\python.exe -c "from shadow.config import settings; print('Meta API key found' if settings.live else 'No MODEL_API_KEY: sample mode only')"
& .venv\Scripts\python.exe -m uvicorn shadow.api:app --port 8000
Pop-Location
