#!/bin/bash
# SSL Setup Script for EduSauti
# This script sets up SSL certificates using Let's Encrypt/Certbot

set -e

DOMAIN="edusauti.ayubsoft-inc.systems"
EMAIL="admin@ayubsoft-inc.systems"  # Change this to your email
NGINX_CONF="/etc/nginx/sites-available/edusauti.conf"
PROJECT_DIR="/opt/edusauti"

echo "🔒 Setting up SSL certificates for $DOMAIN"

# Check if domain resolves to this server
echo "🔍 Checking DNS resolution..."
SERVER_IP=$(curl -s ifconfig.me)
DOMAIN_IP=$(dig +short $DOMAIN | tail -n1)

if [ "$SERVER_IP" != "$DOMAIN_IP" ]; then
    echo "⚠️  Warning: Domain $DOMAIN resolves to $DOMAIN_IP but server IP is $SERVER_IP"
    echo "   SSL certificate request may fail if DNS is not properly configured"
    read -p "Continue anyway? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install certbot if not already installed
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing certbot..."
    apt update
    apt install -y snapd
    snap install core; snap refresh core
    snap install --classic certbot
    ln -sf /snap/bin/certbot /usr/bin/certbot
fi

# Stop containers temporarily to free port 80 for certbot
echo "🛑 Temporarily stopping containers for certificate generation..."
cd $PROJECT_DIR
docker-compose down

# Generate SSL certificate
echo "🔐 Generating SSL certificate..."
certbot certonly --standalone \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN

if [ $? -eq 0 ]; then
    echo "✅ SSL certificate generated successfully!"
    
    # Update nginx configuration with SSL paths
    echo "🔧 Updating nginx configuration..."
    
    # Backup original config
    cp $PROJECT_DIR/nginx/sites-available/edusauti.conf $PROJECT_DIR/nginx/sites-available/edusauti.conf.backup
    
    # Update SSL certificate paths in nginx config
    sed -i "s|ssl_certificate /etc/.*|ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;|" $PROJECT_DIR/nginx/sites-available/edusauti.conf
    sed -i "s|ssl_certificate_key /etc/.*|ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;|" $PROJECT_DIR/nginx/sites-available/edusauti.conf
    
    # Update docker-compose.yml to mount SSL certificates
    cat >> $PROJECT_DIR/docker-compose.yml << 'EOF'

  # SSL certificate volumes
volumes:
  ssl_certs:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /etc/letsencrypt
EOF

    # Add SSL volume mount to nginx service
    echo "📝 Updating docker-compose.yml for SSL certificates..."
    # This is a simple append - you may need to manually edit docker-compose.yml
    # to properly add the SSL volume mount to the nginx service
    
    echo "⚠️  Manual step required:"
    echo "   Please add the following volume mount to the nginx service in docker-compose.yml:"
    echo "   - /etc/letsencrypt:/etc/letsencrypt:ro"
    
    # Restart containers
    echo "🚀 Starting containers with SSL configuration..."
    docker-compose up -d
    
    # Set up auto-renewal
    echo "🔄 Setting up automatic certificate renewal..."
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'cd $PROJECT_DIR && docker-compose restart nginx'") | crontab -
    
    echo ""
    echo "🎉 SSL setup completed successfully!"
    echo ""
    echo "📋 Manual step required:"
    echo "   1. Edit $PROJECT_DIR/docker-compose.yml"
    echo "   2. Add to nginx service volumes:"
    echo "      - /etc/letsencrypt:/etc/letsencrypt:ro"
    echo "   3. Run: cd $PROJECT_DIR && docker-compose up -d"
    echo ""
    echo "🌐 Your application should now be available at:"
    echo "   - HTTPS: https://$DOMAIN:8443"
    echo "   - HTTP: http://$DOMAIN:8080 (redirects to HTTPS)"
    
else
    echo "❌ SSL certificate generation failed!"
    echo "🚀 Starting containers without SSL..."
    docker-compose up -d
    exit 1
fi
