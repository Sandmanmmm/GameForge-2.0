#!/bin/bash

# GameForge Production Deployment Script
set -e

echo "🚀 Starting GameForge Production Deployment..."

# Configuration
ENVIRONMENT=${1:-production}
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if required files exist
check_requirements() {
    log "Checking deployment requirements..."
    
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        error "Docker Compose file not found: $DOCKER_COMPOSE_FILE"
    fi
    
    if [ ! -f ".env.production" ]; then
        error "Production environment file not found: .env.production"
    fi
    
    # Check if required environment variables are set
    if [ -z "$POSTGRES_PASSWORD" ]; then
        error "POSTGRES_PASSWORD environment variable not set"
    fi
    
    if [ -z "$JWT_SECRET" ]; then
        error "JWT_SECRET environment variable not set"
    fi
    
    log "✅ Requirements check passed"
}

# Create backup
create_backup() {
    log "Creating backup..."
    mkdir -p "$BACKUP_DIR"
    
    # Backup database
    if docker ps | grep -q gameforge-postgres; then
        log "Backing up database..."
        docker exec gameforge-postgres pg_dump -U gameforge_user gameforge_production > "$BACKUP_DIR/database_backup.sql"
    fi
    
    # Backup upload files
    if [ -d "./uploads" ]; then
        log "Backing up upload files..."
        cp -r ./uploads "$BACKUP_DIR/"
    fi
    
    log "✅ Backup created at $BACKUP_DIR"
}

# Build and deploy
deploy() {
    log "Building and deploying GameForge..."
    
    # Pull latest images
    log "Pulling latest Docker images..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" pull
    
    # Build custom images
    log "Building custom images..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" build --no-cache
    
    # Stop existing containers
    log "Stopping existing containers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    
    # Start new containers
    log "Starting new containers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    # Wait for services to be healthy
    log "Waiting for services to be healthy..."
    timeout 300 bash -c 'until docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "healthy"; do sleep 5; done'
    
    log "✅ Deployment completed successfully"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" exec backend npm run db:migrate:prod
    log "✅ Database migrations completed"
}

# Health check
health_check() {
    log "Performing health checks..."
    
    # Check backend health
    if curl -f http://localhost:3001/api/health > /dev/null 2>&1; then
        log "✅ Backend health check passed"
    else
        error "Backend health check failed"
    fi
    
    # Check frontend
    if curl -f http://localhost/ > /dev/null 2>&1; then
        log "✅ Frontend health check passed"
    else
        error "Frontend health check failed"
    fi
    
    # Check database connection
    if docker-compose -f "$DOCKER_COMPOSE_FILE" exec postgres pg_isready -U gameforge_user -d gameforge_production > /dev/null 2>&1; then
        log "✅ Database health check passed"
    else
        error "Database health check failed"
    fi
    
    log "✅ All health checks passed"
}

# Cleanup old images and containers
cleanup() {
    log "Cleaning up old Docker images and containers..."
    docker system prune -f
    log "✅ Cleanup completed"
}

# Show deployment status
show_status() {
    log "Deployment Status:"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps
    
    log "\nService URLs:"
    echo "Frontend: http://localhost/"
    echo "Backend API: http://localhost:3001/"
    echo "Grafana: http://localhost:3000/"
    echo "Prometheus: http://localhost:9090/"
}

# Main deployment flow
main() {
    log "🎮 GameForge Production Deployment Started"
    log "Environment: $ENVIRONMENT"
    
    check_requirements
    create_backup
    deploy
    run_migrations
    health_check
    cleanup
    show_status
    
    log "🎉 GameForge deployment completed successfully!"
    log "Monitor the logs with: docker-compose -f $DOCKER_COMPOSE_FILE logs -f"
}

# Handle script interruption
trap 'error "Deployment interrupted"' INT

# Run main function
main "$@"
