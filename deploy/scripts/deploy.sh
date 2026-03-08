#!/bin/bash
# =============================================================================
# Deploy Script - Build and start all services
# =============================================================================
# Usage: ./deploy/scripts/deploy.sh [--build]
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check environment file
if [ ! -f .env ]; then
    log_warn ".env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        log_info ".env created. Please edit it with your actual values!"
        exit 1
    else
        log_error "No .env.example found. Cannot create .env"
        exit 1
    fi
fi

# Build flag
BUILD=false
if [ "$1" = "--build" ] || [ "$1" = "-b" ]; then
    BUILD=true
fi

# Build images if requested
if [ "$BUILD" = true ]; then
    log_info "Building Docker images..."
    docker-compose build --no-cache
else
    log_info "Using existing images (use --build to rebuild)"
fi

# Start services
log_info "Starting SalesMate services..."
docker-compose up -d

# Wait for services to be healthy
log_info "Waiting for services to be healthy..."
sleep 10

# Show status
log_info "Services status:"
docker-compose ps

log_info "Deployment complete!"
log_info "Application: http://localhost:18790"
log_info "API:        http://localhost:18791"
log_info "Redis:      localhost:6379"
log_info "Postgres:   localhost:5432"
log_info "OpenViking: localhost:1933"