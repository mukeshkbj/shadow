# Deploy Shadow to Modal from Windows PowerShell:   .\deploy.ps1
# The live settings live in the Modal secret "shadow-secrets". This script only replaces that secret
# when MODEL_API_KEY is set in this shell, and then it writes every setting below that is set,
# so a plain redeploy never wipes the keys or the upload passcode.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m pip install --quiet --upgrade modal
if (-not (Test-Path "$HOME\.modal.toml") -and -not $env:MODAL_TOKEN_ID) {
    Write-Host "Linking your Modal account (a browser window opens; approve it)..."
    python -m modal setup
}

if ($env:MODEL_API_KEY) {
    $secretArgs = @("SHADOW_WINDOW_SECONDS=0", "MODEL_API_KEY=$env:MODEL_API_KEY")
    foreach ($name in "SHADOW_OPEN_API_KEY", "SHADOW_UPLOAD_PASSCODE") {
        $value = [Environment]::GetEnvironmentVariable($name)
        if ($value) { $secretArgs += "$name=$value" }
    }
    if (-not $env:SHADOW_UPLOAD_PASSCODE) {
        Write-Host "Warning: SHADOW_UPLOAD_PASSCODE is not set, so uploads will be open and review edits will be shared." -ForegroundColor Yellow
    }
    python -m modal secret create shadow-secrets @secretArgs --force
} else {
    Write-Host "MODEL_API_KEY is not set: keeping the existing shadow-secrets secret."
}

Push-Location frontend
npm install --silent
npm run build
Pop-Location

python -m modal deploy modal_app.py
Write-Host "`nDone. Open the https://...modal.run URL printed above." -ForegroundColor Green
