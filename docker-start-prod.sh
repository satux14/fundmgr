#!/bin/bash

# Start Fund Manager in Production Mode (Port 3435)
echo "Starting Fund Management System in Production Mode (Port 3435)..."

docker-compose -f docker-compose.prod.yml up -d

echo "Production server should be running on http://127.0.0.1:3435"
echo "To view logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "To stop: docker-compose -f docker-compose.prod.yml down"

