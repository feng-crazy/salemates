#!/bin/bash
set -e

echo "Running database migrations..."

# Wait for Postgres to be ready
until pg_isready -h postgres -p 5432; do
    echo "Waiting for postgres..."
    sleep 1
done

# Run migrations
psql $DATABASE_URL -f /app/migrations/001_initial_schema.sql

echo "Migrations completed!"