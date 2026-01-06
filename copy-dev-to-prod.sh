#!/bin/bash

# Copy database from dev to prod
# This will overwrite the production database with the development database

echo "Copying database from dev to prod..."
echo "WARNING: This will overwrite the production database!"

read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

# Ensure data-prod directory exists
mkdir -p data-prod

# Copy the database file
cp data/fundmgr.db data-prod/fundmgr.db

echo "Database copied successfully!"
echo "Production database is now at: data-prod/fundmgr.db"
echo ""
echo "To restart the production container with new data:"
echo "  docker-compose -f docker-compose.prod.yml restart"

