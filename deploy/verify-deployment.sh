#!/bin/bash

# EduSauti Deployment Verification Script
# Verifies that the deployment is working correctly

set -e

PROJECT_DIR="/opt/edusauti"
DOMAIN="edusauti.ayubsoft-inc.systems"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

echo "🔍 EduSauti Deployment Verification"
echo "===================================="
echo ""

cd $PROJECT_DIR

# Check if Docker is running
if docker --version > /dev/null 2>&1; then
    print_status "Docker is installed and running"
else
    print_error "Docker is not available"
    exit 1
fi

# Check if Docker Compose is available
if docker-compose --version > /dev/null 2>&1; then
    print_status "Docker Compose is available"
else
    print_error "Docker Compose is not available"
    exit 1
fi

# Check if containers are running
echo ""
print_info "Checking container status..."
if docker-compose ps | grep -q "Up"; then
    print_status "Containers are running"
    docker-compose ps
else
    print_warning "Some containers may not be running"
    docker-compose ps
fi

# Check application health
echo ""
print_info "Checking application health..."
if curl -f http://localhost:8001/health/ > /dev/null 2>&1; then
    print_status "Application health check passed"
    echo "Health check response:"
    curl -s http://localhost:8001/health/ | python3 -m json.tool
else
    print_error "Application health check failed"
    echo "Checking logs..."
    docker-compose logs --tail=20 web
fi

# Check if nginx is serving static files
echo ""
print_info "Checking static file serving..."
if curl -f http://localhost/static/ > /dev/null 2>&1; then
    print_status "Static files are being served"
else
    print_warning "Static files may not be configured correctly"
fi

# Check SSL certificate
echo ""
print_info "Checking SSL certificate..."
if command -v openssl > /dev/null 2>&1; then
    if openssl s_client -connect $DOMAIN:443 -servername $DOMAIN < /dev/null 2>/dev/null | grep -q "Verify return code: 0"; then
        print_status "SSL certificate is valid"
    else
        print_warning "SSL certificate validation failed or not configured"
    fi
else
    print_info "OpenSSL not available for certificate check"
fi

# Check database
echo ""
print_info "Checking database..."
if docker-compose exec -T web python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT 1'); print('Database OK')" 2>/dev/null | grep -q "Database OK"; then
    print_status "Database is accessible"
else
    print_error "Database connection failed"
fi

# Check Redis
echo ""
print_info "Checking Redis..."
if docker-compose exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
    print_status "Redis is responding"
else
    print_error "Redis is not responding"
fi

# Check Celery
echo ""
print_info "Checking Celery workers..."
if docker-compose logs celery 2>/dev/null | grep -q "ready"; then
    print_status "Celery workers are ready"
else
    print_warning "Celery workers may not be ready"
fi

# Check disk space
echo ""
print_info "Checking disk space..."
DISK_USAGE=$(df /opt | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    print_status "Disk usage is acceptable ($DISK_USAGE%)"
else
    print_warning "Disk usage is high ($DISK_USAGE%)"
fi

# Check memory usage
echo ""
print_info "Checking memory usage..."
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ "$MEMORY_USAGE" -lt 80 ]; then
    print_status "Memory usage is acceptable ($MEMORY_USAGE%)"
else
    print_warning "Memory usage is high ($MEMORY_USAGE%)"
fi

# Check log files
echo ""
print_info "Checking log files..."
if [ -f "/app/logs/django.log" ]; then
    LOG_SIZE=$(du -h /app/logs/django.log | cut -f1)
    print_status "Django log file exists ($LOG_SIZE)"
else
    print_warning "Django log file not found"
fi

# Final summary
echo ""
echo "📊 Verification Summary"
echo "======================="
print_info "Application URL: http://$DOMAIN"
print_info "HTTPS URL: https://$DOMAIN"
print_info "Admin URL: https://$DOMAIN/admin/"
print_info "Health Check: https://$DOMAIN/health/"
echo ""
print_info "Useful commands:"
echo "  - View logs: docker-compose logs -f [service]"
echo "  - Restart: docker-compose restart"
echo "  - Status: docker-compose ps"
echo "  - Shell: docker-compose exec web python manage.py shell"
echo "  - Admin: docker-compose exec web python manage.py createsuperuser"
echo ""

if curl -f http://localhost:8001/health/ > /dev/null 2>&1; then
    print_status "🎉 Deployment verification completed successfully!"
else
    print_error "❌ Deployment verification found issues. Check the logs above."
    exit 1
fi
