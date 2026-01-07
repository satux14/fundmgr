#!/bin/bash

# Script to migrate both dev and prod Docker instances
# Usage: ./migrate_both_instances.sh

set -e

echo "=========================================="
echo "Migrating Dev and Prod Instances"
echo "=========================================="
echo ""

# Function to run migration in a container
run_migration_in_container() {
    local compose_file=$1
    local service_name=$2
    local instance_name=$3
    
    echo "Migrating $instance_name instance..."
    
    # Get the actual container name
    CONTAINER_ID=$(docker-compose -f "$compose_file" ps -q "$service_name" 2>/dev/null | head -1)
    
    if [ -z "$CONTAINER_ID" ]; then
        echo "  Container for $service_name is not running"
        echo "  Starting container..."
        docker-compose -f "$compose_file" up -d "$service_name"
        sleep 3
        CONTAINER_ID=$(docker-compose -f "$compose_file" ps -q "$service_name" 2>/dev/null | head -1)
    fi
    
    if [ -n "$CONTAINER_ID" ]; then
        CONTAINER_NAME=$(docker ps --format '{{.Names}}' --filter id=$CONTAINER_ID | head -1)
        echo "  Running migration in container: $CONTAINER_NAME"
        docker exec "$CONTAINER_NAME" python migrate_add_fund_status.py
        if [ $? -eq 0 ]; then
            echo "  ✓ $instance_name migration completed successfully"
        else
            echo "  ✗ $instance_name migration failed"
            return 1
        fi
    else
        echo "  ✗ Could not start or find container for $service_name"
        return 1
    fi
    echo ""
}

# Migrate Dev instance
if [ -f "docker-compose.dev.yml" ]; then
    echo "1. Migrating DEV instance..."
    run_migration_in_container "docker-compose.dev.yml" "fundmgr-app" "DEV" || echo "  Warning: DEV migration had issues"
else
    echo "1. DEV instance: docker-compose.dev.yml not found, skipping..."
    echo ""
fi

# Migrate Prod instance
if [ -f "docker-compose.prod.yml" ]; then
    echo "2. Migrating PROD instance..."
    run_migration_in_container "docker-compose.prod.yml" "fundmgr-app-prod" "PROD" || echo "  Warning: PROD migration had issues"
else
    echo "2. PROD instance: docker-compose.prod.yml not found, skipping..."
    echo ""
fi

# Also migrate local databases if they exist (for manual testing)
echo "3. Migrating local databases (if they exist)..."
if [ -f "data/fundmgr.db" ] || [ -f "data-prod/fundmgr.db" ]; then
    if command -v python3 &> /dev/null; then
        echo "  Running local migration with python3..."
        python3 migrate_add_fund_status.py
    elif command -v python &> /dev/null; then
        echo "  Running local migration with python..."
        python migrate_add_fund_status.py
    else
        echo "  Python not found, skipping local migration"
    fi
else
    echo "  No local databases found, skipping..."
fi

echo ""
echo "=========================================="
echo "All migrations completed!"
echo "=========================================="
echo ""
echo "Note: If containers were started, you may want to check their status:"
echo "  docker-compose -f docker-compose.dev.yml ps"
echo "  docker-compose -f docker-compose.prod.yml ps"

