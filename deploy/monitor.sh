#!/bin/bash

# EduSauti Monitoring Script
# Monitors application health and restarts if needed

set -e

PROJECT_DIR="/opt/edusauti"
LOG_FILE="/var/log/edusauti-monitor.log"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | sudo tee -a $LOG_FILE
}

# Function to check application health
check_health() {
    local url="http://localhost:8000/health/"
    local response=$(curl -s -o /dev/null -w "%{http_code}" $url 2>/dev/null || echo "000")
    
    if [ "$response" = "200" ]; then
        return 0
    else
        return 1
    fi
}

# Function to restart application
restart_application() {
    log_message "🔄 Restarting EduSauti application..."
    cd $PROJECT_DIR
    docker-compose restart web
    sleep 30
}

# Function to send alert (you can customize this)
send_alert() {
    local message="$1"
    log_message "🚨 ALERT: $message"
    # You can add email or Slack notifications here
}

# Main monitoring loop
main() {
    log_message "🔍 Starting health check..."
    
    # Check if Docker containers are running
    cd $PROJECT_DIR
    if ! docker-compose ps | grep -q "Up"; then
        log_message "❌ Docker containers are not running"
        send_alert "EduSauti containers are down"
        
        # Try to start containers
        log_message "🚀 Starting containers..."
        docker-compose up -d
        sleep 60
    fi
    
    # Check application health
    if check_health; then
        log_message "✅ Application is healthy"
    else
        log_message "❌ Application health check failed"
        send_alert "EduSauti application is unhealthy"
        
        # Try to restart
        restart_application
        
        # Check again after restart
        sleep 30
        if check_health; then
            log_message "✅ Application recovered after restart"
        else
            log_message "❌ Application still unhealthy after restart"
            send_alert "EduSauti application failed to recover"
        fi
    fi
    
    # Check disk space
    local disk_usage=$(df /opt | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 80 ]; then
        log_message "⚠️ Disk usage is high: ${disk_usage}%"
        send_alert "High disk usage: ${disk_usage}%"
    fi
    
    # Check container resource usage
    local containers=$(docker-compose ps -q)
    for container in $containers; do
        local stats=$(docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" $container)
        log_message "📊 Container stats: $stats"
    done
}

# Run the monitoring check
main
