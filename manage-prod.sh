#!/bin/bash

# EduSauti Production Management Script
# Provides common management tasks for the production environment

set -e

PROJECT_DIR="/opt/edusauti"
COMPOSE_FILE="docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Ensure we're in the right directory
cd $PROJECT_DIR

# Function to show help
show_help() {
    echo "EduSauti Production Management Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start        Start all services"
    echo "  stop         Stop all services"
    echo "  restart      Restart all services"
    echo "  status       Show service status"
    echo "  logs         Show application logs"
    echo "  shell        Open Django shell"
    echo "  dbshell      Open database shell"
    echo "  migrate      Run database migrations"
    echo "  collectstatic Collect static files"
    echo "  createsuperuser Create Django superuser"
    echo "  backup       Create backup"
    echo "  update       Update application"
    echo "  health       Check application health"
    echo "  clean        Clean up unused Docker resources"
    echo "  help         Show this help message"
}

# Function to check if services are running
check_services() {
    if docker-compose ps | grep -q "Up"; then
        return 0
    else
        return 1
    fi
}

# Main command processing
case "$1" in
    start)
        print_header "Starting EduSauti Services"
        docker-compose up -d
        print_status "Services started"
        docker-compose ps
        ;;
    
    stop)
        print_header "Stopping EduSauti Services"
        docker-compose down
        print_status "Services stopped"
        ;;
    
    restart)
        print_header "Restarting EduSauti Services"
        docker-compose restart
        print_status "Services restarted"
        docker-compose ps
        ;;
    
    status)
        print_header "Service Status"
        docker-compose ps
        echo ""
        print_status "Container resource usage:"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
        ;;
    
    logs)
        if [ -n "$2" ]; then
            docker-compose logs -f "$2"
        else
            docker-compose logs -f web
        fi
        ;;
    
    shell)
        print_header "Django Shell"
        docker-compose exec web python manage.py shell
        ;;
    
    dbshell)
        print_header "Database Shell"
        docker-compose exec web python manage.py dbshell
        ;;
    
    migrate)
        print_header "Running Database Migrations"
        docker-compose exec web python manage.py migrate
        print_status "Migrations completed"
        ;;
    
    collectstatic)
        print_header "Collecting Static Files"
        docker-compose exec web python manage.py collectstatic --noinput
        print_status "Static files collected"
        ;;
    
    createsuperuser)
        print_header "Creating Superuser"
        docker-compose exec web python manage.py createsuperuser
        ;;
    
    backup)
        print_header "Creating Backup"
        ./deploy/backup.sh
        ;;
    
    update)
        print_header "Updating Application"
        ./deploy/deploy.sh
        ;;
    
    health)
        print_header "Health Check"
        if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
            print_status "✅ Application is healthy"
            curl -s http://localhost:8000/health/ | python -m json.tool
        else
            print_error "❌ Application health check failed"
            exit 1
        fi
        ;;
    
    clean)
        print_header "Cleaning Docker Resources"
        print_warning "This will remove unused Docker images and volumes"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker system prune -f
            docker volume prune -f
            print_status "Cleanup completed"
        else
            print_status "Cleanup cancelled"
        fi
        ;;
    
    help|--help|-h)
        show_help
        ;;
    
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
