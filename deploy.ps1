# Deploy Shadow to Modal from Windows PowerShell:   .\deploy.ps1
# Optional: $env:MODEL_API_KEY = "<meta key>" before running, so uploads work live.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m pip install --quiet --upgrade modal
if (-not (Test-Path "$HOME\.modal.toml")) {
    Write-Host "Linking your Modal account (a browser window opens; approve it)..."
    python -m modal setup
}

# Secret with settings for the live app. Re-run with MODEL_API_KEY set to add the Meta key later.
$secretArgs = @("SHADOW_WINDOW_SECONDS=0")
if ($env:MODEL_API_KEY) { $secretArgs += "MODEL_API_KEY=$env:MODEL_API_KEY" }
if ($env:SHADOW_OPEN_BASE_URL -and $env:SHADOW_OPEN_API_KEY) {
    $secretArgs += "SHADOW_OPEN_BASE_URL=$env:SHADOW_OPEN_BASE_URL"
    $secretArgs += "SHADOW_OPEN_API_KEY=$env:SHADOW_OPEN_API_KEY"
}
python -m modal secret create shadow-secrets @secretArgs --force

Push-Location frontend
npm install --silent
npm run build
Pop-Location

python -m modal deploy modal_app.py
Write-Host "`nDone. Open the https://...modal.run URL printed above." -ForegroundColor Green
