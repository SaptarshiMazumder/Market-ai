@echo off
echo ========================================
echo Starting MarketAI
echo ========================================
echo.

echo Starting backend server...
start cmd /k "cd backend && venv\Scripts\activate && python app.py"

timeout /t 3 /nobreak > nul

echo Starting frontend server...
start cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo MarketAI is starting!
echo ========================================
echo.
echo Backend: http://localhost:5000
echo Frontend: http://localhost:5173
echo.
echo Press any key to stop all servers...
pause > nul

taskkill /fi "WINDOWTITLE eq *backend*" /f
taskkill /fi "WINDOWTITLE eq *frontend*" /f
