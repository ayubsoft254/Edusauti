#!/bin/bash

# Docker Container Fix Script for EduSauti
# This script fixes container restart loops and port conflicts

set -e

echo "🔧 EduSauti Container Fix Script"
echo "================================"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Change to project directory
cd "$PROJECT_DIR"

echo "Working directory: $(pwd)"
echo ""

# Function to wait for container to be healthy
wait_for_container() {
    local container_name=$1
    local max_wait=60
    local wait_time=0
    
    echo "⏳ Waiting for $container_name to be ready..."
    
    while [ $wait_time -lt $max_wait ]; do
        if docker-compose ps $container_name | grep -q "Up"; then
            echo "✅ $container_name is ready"
            return 0
        fi
        
        if docker-compose ps $container_name | grep -q "Exit"; then
            echo "❌ $container_name has exited"
            return 1
        fi
        
        sleep 5
        wait_time=$((wait_time + 5))
        echo "   Waiting... ($wait_time/${max_wait}s)"
    done
    
    echo "❌ Timeout waiting for $container_name"
    return 1
}

# Step 1: Check current status
echo "📊 Checking current container status..."
docker-compose ps

echo ""
echo "📋 Checking container logs for errors..."
docker-compose logs --tail=20 web || true
docker-compose logs --tail=20 celery || true
docker-compose logs --tail=20 redis || true

# Function to check if we're in the right directory
check_project_directory() {
    if [ ! -f "docker-compose.yml" ]; then
        echo "❌ Error: docker-compose.yml not found!"
        echo "Please run this script from the project root directory."
        exit 1
    fi
    echo "✓ Found docker-compose.yml"
}

# Function to show current container status
show_container_status() {
    echo "=== Current Container Status ==="
    sudo docker-compose ps || echo "No containers running"
    echo ""
}

# Function to show container logs
show_recent_logs() {
    echo "=== Recent Container Logs ==="
    sudo docker-compose logs --tail=20 || echo "No logs available"
    echo ""
}

# Function to check for port conflicts
check_port_conflicts() {
    echo "=== Checking for Port Conflicts ==="
    
    ports_to_check=(80 443 6379 8000 8080 8443)
    conflicts_found=false
    
    for port in "${ports_to_check[@]}"; do
        if sudo netstat -tulpn 2>/dev/null | grep ":$port " | grep -v docker; then
            echo "⚠ Port $port is in use by non-Docker process"
            conflicts_found=true
        fi
    done
    
    if [ "$conflicts_found" = false ]; then
        echo "✓ No port conflicts detected"
    fi
    echo ""
}

# Function to stop all containers
stop_containers() {
    echo "=== Stopping All Containers ==="
    sudo docker-compose down --volumes --remove-orphans 2>/dev/null || echo "No containers to stop"
    echo "✓ Containers stopped"
    echo ""
}

# Function to clean up Docker resources
cleanup_docker() {
    echo "=== Cleaning Up Docker Resources ==="
    
    # Remove stopped containers
    sudo docker container prune -f
    
    # Remove unused networks
    sudo docker network prune -f
    
    # Remove unused volumes (be careful with this)
    read -p "Do you want to remove unused Docker volumes? This may delete data! (y/N): " remove_volumes
    if [[ "$remove_volumes" =~ ^[Yy]$ ]]; then
        sudo docker volume prune -f
        echo "✓ Volumes cleaned up"
    else
        echo "✓ Volumes preserved"
    fi
    
    echo "✓ Docker cleanup completed"
    echo ""
}

# Function to check system resources
check_resources() {
    echo "=== System Resources Check ==="
    echo "Disk usage:"
    df -h | head -2
    echo ""
    echo "Memory usage:"
    free -h
    echo ""
    echo "Docker system usage:"
    sudo docker system df 2>/dev/null || echo "Docker system info not available"
    echo ""
}

# Function to rebuild containers
rebuild_containers() {
    echo "=== Rebuilding Containers ==="
    echo "This may take a few minutes..."
    
    # Build without cache to ensure clean build
    sudo docker-compose build --no-cache
    
    echo "✓ Containers rebuilt"
    echo ""
}

# Function to start containers one by one
start_containers_step_by_step() {
    echo "=== Starting Containers Step by Step ==="
    
    # Start Redis first
    echo "Starting Redis..."
    sudo docker-compose up -d redis
    sleep 10
    
    if sudo docker-compose ps | grep redis | grep -q "Up"; then
        echo "✓ Redis started successfully"
    else
        echo "❌ Redis failed to start"
        sudo docker-compose logs redis
        return 1
    fi
    
    # Start web container
    echo "Starting Web container..."
    sudo docker-compose up -d web
    sleep 15
    
    if sudo docker-compose ps | grep web | grep -q "Up"; then
        echo "✓ Web container started successfully"
    else
        echo "❌ Web container failed to start"
        sudo docker-compose logs web
        return 1
    fi
    
    # Start celery
    echo "Starting Celery..."
    sudo docker-compose up -d celery
    sleep 10
    
    if sudo docker-compose ps | grep celery | grep -q "Up"; then
        echo "✓ Celery started successfully"
    else
        echo "❌ Celery failed to start"
        sudo docker-compose logs celery
        return 1
    fi
    
    # Start nginx
    echo "Starting Nginx..."
    sudo docker-compose up -d nginx
    sleep 10
    
    if sudo docker-compose ps | grep nginx | grep -q "Up"; then
        echo "✓ Nginx started successfully"
    else
        echo "❌ Nginx failed to start"
        sudo docker-compose logs nginx
        return 1
    fi
    
    echo ""
    echo "✅ All containers started successfully!"
    echo ""
}

# Function to verify deployment
verify_deployment() {
    echo "=== Verifying Deployment ==="
    
    # Wait a moment for services to be fully ready
    echo "Waiting for services to be ready..."
    sleep 30
    
    # Check container status
    echo "Container status:"
    sudo docker-compose ps
    echo ""
    
    # Test health endpoint
    echo "Testing application health..."
    if curl -f http://localhost:8080/health/ >/dev/null 2>&1; then
        echo "✓ Health check passed"
    else
        echo "⚠ Health check failed - application may still be starting"
    fi
    
    # Test main application
    echo "Testing main application..."
    if curl -f http://localhost:8080 >/dev/null 2>&1; then
        echo "✓ Application is responding"
    else
        echo "⚠ Application not responding - check logs"
    fi
    
    echo ""
}

# Function to show final status and next steps
show_final_status() {
    echo "=== Final Status ==="
    sudo docker-compose ps
    echo ""
    
    echo "=== Access Information ==="
    echo "Your application should be available at:"
    echo "- HTTP:  http://$(hostname -I | awk '{print $1}'):8080"
    echo "- HTTPS: https://$(hostname -I | awk '{print $1}'):8443"
    echo ""
    
    echo "=== Useful Commands ==="
    echo "View logs:           sudo docker-compose logs -f"
    echo "Check status:        sudo docker-compose ps"
    echo "Restart service:     sudo docker-compose restart <service_name>"
    echo "Stop all:           sudo docker-compose down"
    echo "Start all:          sudo docker-compose up -d"
    echo ""
}

# Main execution
main() {
    echo "Starting container fix process..."
    echo ""
    
    # Confirmation prompt
    read -p "This will stop, clean up, and restart all containers. Continue? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Operation cancelled."
        exit 0
    fi
    
    echo ""
    
    # Run fix steps
    check_project_directory
    show_container_status
    show_recent_logs
    check_port_conflicts
    check_resources
    stop_containers
    cleanup_docker
    rebuild_containers
    start_containers_step_by_step
    verify_deployment
    show_final_status
    
    echo "🎉 Container fix completed!"
    echo ""
    echo "If you still have issues, check the logs with:"
    echo "sudo docker-compose logs <service_name>"
}

# Run main function
main "$@"
