#!/bin/bash
# Docker startup script

echo "Starting Chit Fund Management System in Docker..."

# Build and start containers
echo "Building and starting Docker containers..."
docker-compose up -d --build

echo ""
echo "✅ Server is starting on http://localhost:3434"
echo "   (The database will be automatically seeded on first run)"
echo ""
echo "Admin login:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"

