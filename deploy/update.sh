#!/bin/bash

# EduSauti Application Update Script
# This script handles updates to the deployed application

set -e

echo "🔄 EduSauti Application Update Script"
echo "====================================="

# Configuration
APP_DIR="/opt/edusauti"
BACKUP_DIR="/opt/edusauti/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found. Please run this script from the application directory."
    exit 1
fi

# Function to create backup before update
create_backup() {
    echo "📦 Creating backup before update..."
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    # Backup SQLite database
    if [ -f "data/db.sqlite3" ]; then
        cp data/db.sqlite3 "$BACKUP_DIR/db_backup_$TIMESTAMP.sqlite3"
        echo "✅ Database backed up to $BACKUP_DIR/db_backup_$TIMESTAMP.sqlite3"
    fi
    
    # Backup media files
    if [ -d "media" ]; then
        tar -czf "$BACKUP_DIR/media_backup_$TIMESTAMP.tar.gz" media/
        echo "✅ Media files backed up to $BACKUP_DIR/media_backup_$TIMESTAMP.tar.gz"
    fi
    
    # Backup environment file
    if [ -f ".env.production" ]; then
        cp .env.production "$BACKUP_DIR/env_backup_$TIMESTAMP"
        echo "✅ Environment file backed up"
    fi
}

# Function to pull latest changes from Git
pull_changes() {
    echo "🔄 Pulling latest changes from Git repository..."
    
    # Check if Git repository exists
    if [ ! -d ".git" ]; then
        echo "❌ Error: Not a Git repository. Please clone the repository first."
        exit 1
    fi
    
    # Pull latest changes
    git fetch origin
    git pull origin main
    
    echo "✅ Latest changes pulled successfully"
}

# Function to rebuild and restart containers
rebuild_containers() {
    echo "🔨 Rebuilding and restarting containers..."
    
    # Stop containers
    docker-compose down
    
    # Remove old images (optional - saves disk space)
    docker image prune -f
    
    # Build and start containers
    docker-compose up --build -d
    
    echo "✅ Containers rebuilt and restarted"
}

# Function to run database migrations
run_migrations() {
    echo "🗄️ Running database migrations..."
    
    # Wait for containers to be ready
    sleep 10
    
    # Run migrations
    docker-compose exec web python manage.py migrate
    
    # Collect static files
    docker-compose exec web python manage.py collectstatic --noinput
    
    echo "✅ Migrations completed"
}

# Function to verify deployment
verify_deployment() {
    echo "🔍 Verifying deployment..."
    
    # Wait a moment for services to start
    sleep 5
    
    # Check if containers are running
    if ! docker-compose ps | grep -q "Up"; then
        echo "❌ Error: Some containers are not running"
        docker-compose ps
        exit 1
    fi
    
    # Check health endpoint
    if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
        echo "✅ Health check passed"
    else
        echo "❌ Health check failed"
        exit 1
    fi
    
    echo "✅ Deployment verification completed"
}

# Main update process
main() {
    echo "Starting update process..."
    echo ""
    
    # Step 1: Create backup
    create_backup
    echo ""
    
    # Step 2: Pull changes
    pull_changes
    echo ""
    
    # Step 3: Rebuild containers
    rebuild_containers
    echo ""
    
    # Step 4: Run migrations
    run_migrations
    echo ""
    
    # Step 5: Verify deployment
    verify_deployment
    echo ""
    
    echo "🎉 Update completed successfully!"
    echo ""
    echo "📊 Container status:"
    docker-compose ps
    echo ""
    echo "📝 To view logs: ./manage-prod.sh logs"
    echo "📈 To monitor: ./deploy/monitor.sh"
}

# Run main function
main
