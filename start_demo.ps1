# CHRONOS Start Demo Script
# This scripts launches the FastAPI backend and the Vite frontend concurrently.

Write-Host "Starting CHRONOS System..." -ForegroundColor Green

# 1. Start FastAPI Backend in background
Write-Host "Starting FastAPI Backend (Port 8000)..." -ForegroundColor Cyan
Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--reload" -WorkingDirectory "c:\Users\praba\OneDrive\Desktop\chronoa\ui"

# 2. Start Vite React Frontend
Write-Host "Starting React Frontend (Port 5173)..." -ForegroundColor Cyan
Set-Location -Path "c:\Users\praba\OneDrive\Desktop\chronoa\ui\frontend"
npm run dev
