#!/bin/bash

# Script to run migration for both dev and prod databases
# Usage: ./run_migration.sh

echo "=========================================="
echo "Running Fund Status Migration"
echo "=========================================="
echo ""

# Check if running in Docker or locally
if [ -f "/app/data/fundmgr.db" ]; then
    # Running inside Docker container
    echo "Running inside Docker container..."
    python migrate_add_fund_status.py
else
    # Running locally - need to check for Python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "Error: Python not found. Please install Python 3."
        exit 1
    fi
    
    echo "Running locally with $PYTHON_CMD..."
    $PYTHON_CMD migrate_add_fund_status.py
fi

echo ""
echo "=========================================="
echo "Migration completed!"
echo "=========================================="

