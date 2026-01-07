#!/bin/bash
# Docker entrypoint script

set -e

echo "Starting Fund Management System..."

# Wait for database to be ready (if using external DB)
# For SQLite, we can proceed immediately

# Check if database exists, if not, seed it
if [ ! -f "/app/data/fundmgr.db" ]; then
    echo "Database not found. Seeding initial data..."
    python seed_data.py
    echo "Database seeded successfully!"
else
    echo "Database already exists. Running migrations..."
    python migrate_db.py
    python migrate_add_monthly_payment.py
    python migrate_add_customer_fields.py
    python migrate_add_payment_fields.py
    python migrate_add_fund_status.py
    python migrate_add_audit_log.py
    python migrate_add_guest_visible.py
    # Ensure guest user exists
    python create_guest_user.py
fi

# Start the application
echo "Starting uvicorn server on port 3434..."
exec "$@"

