#!/bin/bash

# EduSauti Deployment Script for Ubuntu Server
# Run this script on your Ubuntu server to set up the deployment environment

set -e

echo "🚀 Starting EduSauti deployment setup..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
else
    echo "Docker is already installed"
fi

# Install Docker Compose
echo "🔧 Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
else
    echo "Docker Compose is already installed"
fi

# Install nginx (for reverse proxy)
echo "🌐 Installing nginx..."
sudo apt install nginx -y

# Install certbot for SSL certificates
echo "🔒 Installing Certbot for SSL..."
sudo apt install certbot python3-certbot-nginx -y

# Create application directory
echo "📁 Creating application directory..."
sudo mkdir -p /opt/edusauti
sudo chown $USER:$USER /opt/edusauti

# Create logs directory
mkdir -p /opt/edusauti/logs

# Create SSL directory
sudo mkdir -p /etc/nginx/ssl

echo "✅ Initial setup completed!"
echo ""
echo "Next steps:"
echo "1. Copy your project files to /opt/edusauti/"
echo "2. Configure your .env.production file"
echo "3. Generate SSL certificates with: sudo certbot --nginx -d edusauti.ayubsoft-inc.systems"
echo "4. Run ./deploy.sh to start the application"
echo ""
echo "📖 For detailed instructions, see the deployment guide."
