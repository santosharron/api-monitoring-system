#!/bin/bash
echo "Starting API Monitoring System Setup..."

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Run the API monitoring setup script
python api_monitoring_setup.py

# Keep terminal open for viewing results
echo "Press Enter to exit..."
read 