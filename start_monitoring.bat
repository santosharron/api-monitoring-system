@echo off
echo Starting API Monitoring System Setup...

rem Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
)

rem Run the API monitoring setup script
python api_monitoring_setup.py

rem Keep the window open to view results
pause 