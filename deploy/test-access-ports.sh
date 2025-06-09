#!/bin/bash

# Test script to check which ports are accessible for EduSauti
echo "🔍 Testing EduSauti Port Access"
echo "==============================="

# Test direct web service (port 8001)
echo "1. Testing direct web service (port 8001)..."
if curl -f http://localhost:8001/health/ > /dev/null 2>&1; then
    echo "✅ Port 8001 (direct web) - WORKING"
else
    echo "❌ Port 8001 (direct web) - NOT WORKING"
fi

# Test nginx HTTP (port 8080)
echo "2. Testing nginx HTTP (port 8080)..."
if curl -f http://localhost:8080/health/ > /dev/null 2>&1; then
    echo "✅ Port 8080 (nginx HTTP) - WORKING"
else
    echo "❌ Port 8080 (nginx HTTP) - NOT WORKING"
fi

# Test nginx HTTPS (port 8443)
echo "3. Testing nginx HTTPS (port 8443)..."
if curl -f -k https://localhost:8443/health/ > /dev/null 2>&1; then
    echo "✅ Port 8443 (nginx HTTPS) - WORKING"
else
    echo "❌ Port 8443 (nginx HTTPS) - NOT WORKING"
fi

# Check what's listening on standard ports
echo ""
echo "4. Checking what's using standard ports 80 and 443..."
if command -v netstat > /dev/null 2>&1; then
    echo "Port 80:"
    netstat -tulpn 2>/dev/null | grep ":80 " || echo "  Nothing found"
    echo "Port 443:"
    netstat -tulpn 2>/dev/null | grep ":443 " || echo "  Nothing found"
fi

echo ""
echo "📋 Access URLs:"
echo "   - Direct web: http://localhost:8001"
echo "   - Via nginx HTTP: http://localhost:8080"
echo "   - Via nginx HTTPS: https://localhost:8443"
echo "   - External HTTP: http://edusauti.ayubsoft-inc.systems:8080"
echo "   - External HTTPS: https://edusauti.ayubsoft-inc.systems:8443"
