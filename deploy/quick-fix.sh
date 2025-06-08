#!/bin/bash

# Quick Container Restart Script
# Simple script to quickly restart containers when they're stuck

set -e

echo "=== Quick Container Fix ==="
echo "=========================="

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Run this script from the project directory containing docker-compose.yml"
    exit 1
fi

echo "🔄 Stopping all containers..."
sudo docker-compose down --remove-orphans

echo "🧹 Cleaning up stuck containers..."
sudo docker container prune -f

echo "🚀 Starting containers..."
sudo docker-compose up -d

echo "⏳ Waiting for containers to start..."
sleep 30

echo "📊 Container status:"
sudo docker-compose ps

echo ""
echo "✅ Quick fix completed!"
echo ""
echo "Access your application at:"
echo "- HTTP:  http://localhost:8080"
echo "- HTTPS: https://localhost:8443"
echo ""
echo "If issues persist, run the full fix script: ./deploy/fix-containers.sh"
