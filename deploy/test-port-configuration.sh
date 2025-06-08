#!/bin/bash

# Test script to verify port configuration is correct
# This script verifies that all ports are correctly configured

set -e

PROJECT_DIR="/opt/edusauti"
cd $PROJECT_DIR

echo "🔍 Testing Port Configuration"
echo "=============================="

# Test 1: Check docker-compose.yml port mapping
echo "1. Checking docker-compose.yml port mapping..."
if grep -q "8001:8000" docker-compose.yml; then
    echo "✅ Docker Compose maps external port 8001 to internal port 8000"
else
    echo "❌ Port mapping not found in docker-compose.yml"
    exit 1
fi

# Test 2: Check nginx upstream configuration
echo "2. Checking nginx upstream configuration..."
if grep -q "server web:8000" nginx/sites-available/edusauti.conf; then
    echo "✅ Nginx upstream points to web:8000 (correct internal port)"
else
    echo "❌ Nginx upstream configuration incorrect"
    exit 1
fi

# Test 3: Check deployment scripts use correct port
echo "3. Checking deployment scripts..."
if grep -q "localhost:8001" deploy/verify-deployment.sh; then
    echo "✅ verify-deployment.sh uses port 8001"
else
    echo "❌ verify-deployment.sh port incorrect"
    exit 1
fi

if grep -q "localhost:8001" deploy/update.sh; then
    echo "✅ update.sh uses port 8001"
else
    echo "❌ update.sh port incorrect"
    exit 1
fi

if grep -q "localhost:8001" deploy/monitor.sh; then
    echo "✅ monitor.sh uses port 8001"
else
    echo "❌ monitor.sh port incorrect"
    exit 1
fi

# Test 4: Check for any remaining references to localhost:8000
echo "4. Checking for any remaining localhost:8000 references..."
if grep -r "localhost:8000" deploy/ --exclude="*.log" --exclude="test-port-configuration.sh"; then
    echo "❌ Found remaining localhost:8000 references"
    exit 1
else
    echo "✅ No remaining localhost:8000 references found"
fi

# Test 5: Check port conflict monitoring
echo "5. Checking port conflict monitoring..."
if grep -q "8001" deploy/fix-containers.sh; then
    echo "✅ fix-containers.sh monitors port 8001"
else
    echo "❌ fix-containers.sh port monitoring incorrect"
    exit 1
fi

echo ""
echo "✅ All port configuration tests passed!"
echo "🎯 Configuration Summary:"
echo "   - External port: 8001 (host machine)"
echo "   - Internal port: 8000 (container)"
echo "   - Nginx upstream: web:8000 (internal Docker network)"
echo "   - Health checks: localhost:8001 (from host)"
echo ""
echo "Ready for deployment! 🚀"
