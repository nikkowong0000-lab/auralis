# Build a standalone Windows .exe with PyInstaller (optional portfolio artifact).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

python -m pip install -r requirements.txt pyinstaller --quiet
$env:PYTHONPATH = "$PWD\src"

python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name Auralis `
  --paths src `
  --add-data "data/presets;data/presets" `
  main.py

Write-Host "Done: dist\Auralis\Auralis.exe"
