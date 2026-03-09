#!/bin/bash
# =============================================================================
# Stop Script - Stop all services
# =============================================================================
# Usage: ./deploy/scripts/stop.sh [--volumes]
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Stopping SaleMates services..."
docker-compose down

# Remove volumes if requested
if [ "$1" = "--volumes" ] || [ "$1" = "-v" ]; then
    echo "Removing volumes..."
    docker-compose down -v
    echo "Volumes removed."
fi

echo "Services stopped."