@echo off
echo ========================================
echo MarketAI Setup Script
echo ========================================
echo.

echo [1/4] Setting up backend...
cd backend
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
echo Backend setup complete!
echo.

echo [2/4] Setting up frontend...
cd ..\frontend
call npm install
echo Frontend setup complete!
echo.

echo [3/4] Creating environment file...
cd ..\backend
if not exist .env (
    copy .env.example .env
    echo .env file created! Please add your API keys.
) else (
    echo .env file already exists.
)
echo.

echo [4/4] Creating required directories...
if not exist uploads mkdir uploads
if not exist generated mkdir generated
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit backend\.env and add your API keys
echo 2. Run start.bat to launch the application
echo.
pause
