#!/bin/bash
# Run script for Chit Fund Management System

echo "Starting Chit Fund Management System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/.installed" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    touch venv/.installed
fi

# Check if database is seeded
if [ ! -f "data/fundmgr.db" ]; then
    echo "Seeding initial data..."
    python seed_data.py
fi

# Run the application
echo "Starting server on http://localhost:3434"
uvicorn app.main:app --reload --host 0.0.0.0 --port 3434

