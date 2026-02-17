# MarketAI Startup Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting MarketAI" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start Backend
Write-Host "Starting Backend Server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; .\venv\Scripts\Activate.ps1; python app.py"

Start-Sleep -Seconds 3

# Start Frontend
Write-Host "Starting Frontend Server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "MarketAI is starting!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend:  http://localhost:5000" -ForegroundColor White
Write-Host "Frontend: http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "Two new windows will open - one for backend, one for frontend" -ForegroundColor Gray
Write-Host "Press Ctrl+C in this window to exit" -ForegroundColor Gray
Write-Host ""

# Keep script running
Read-Host "Press Enter to close"
