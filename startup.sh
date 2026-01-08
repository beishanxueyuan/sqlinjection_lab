#!/bin/bash

set -e

echo "Starting database services..."

# Start MySQL in background
service mysql start
echo "MySQL started"

# Start PostgreSQL in background
chown -R postgres:postgres /var/lib/postgresql
chmod 700 /var/lib/postgresql/*/main/
service postgresql start
echo "PostgreSQL started"

# Start ClickHouse in background
service clickhouse-server start
echo "ClickHouse started"

# Wait a bit for services to fully start
sleep 10

# Initialize databases
echo "Initializing databases..."
python3 /app/init_db.py

# Start the web application
echo "Starting web application..."
cd /app
python3 app.py