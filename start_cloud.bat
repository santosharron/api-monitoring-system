@echo off
echo Starting API Monitoring System with cloud settings...

rem Load cloud environment variables
call cloud_env.bat

rem Verify MongoDB connection first
echo Verifying MongoDB connection...
python verify_mongodb.py
if %ERRORLEVEL% NEQ 0 (
    echo MongoDB connection failed. Please check your credentials and network connection.
    echo Press any key to exit...
    pause > nul
    exit /b 1
)

echo MongoDB connection successful. Starting the application...
python -m src.main

echo Press any key to exit...
pause > nul 