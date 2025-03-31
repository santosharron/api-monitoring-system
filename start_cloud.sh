#!/bin/bash
echo "Starting API Monitoring System with cloud settings..."

# Load cloud environment variables
source ./cloud_env.sh

# Verify MongoDB connection
echo "Verifying MongoDB connection..."
python verify_mongodb.py
if [ $? -ne 0 ]; then
    echo "MongoDB connection failed. Please check your credentials and network connection."
    echo "Press any key to exit..."
    read -n 1
    exit 1
fi

echo "MongoDB connection successful. Starting the application..."
python -m src.main

echo "Press any key to exit..."
read -n 1 