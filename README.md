# EduSauti - AI-Powered Document Processing Platform

EduSauti is a Django-based web application that provides AI-powered document processing capabilities using Azure Cognitive Services.

## 🚀 Quick Start (Production Deployment)

### Prerequisites
- Ubuntu server with Docker and Docker Compose
- Domain name pointing to your server
- SSL certificates (Let's Encrypt recommended)

### Deployment Steps

1. **Server Setup**
   ```bash
   ./deploy/setup-server.sh
   ```

2. **Configure Environment**
   ```bash
   cp .env.production.example .env.production
   # Edit .env.production with your values
   ```

3. **Deploy Application**
   ```bash
   ./deploy/deploy.sh
   ```

4. **Setup SSL**
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

## 🐳 Docker Services

- **web**: Django application (Gunicorn + Uvicorn)
- **db**: PostgreSQL database
- **redis**: Redis for caching and Celery
- **celery**: Background task worker
- **celery-beat**: Scheduled task scheduler
- **nginx**: Reverse proxy and static file server

## 🛠️ Management

Use the production management script:

```bash
# Start services
./manage-prod.sh start

# Check status
./manage-prod.sh status

# View logs
./manage-prod.sh logs

# Run migrations
./manage-prod.sh migrate

# Create backup
./manage-prod.sh backup

# Health check
./manage-prod.sh health
```

## 📁 Project Structure

```
EduSauti/
├── src/                    # Django application
│   ├── core/              # Project settings and configuration
│   ├── users/             # User management
│   ├── documents/         # Document processing
│   ├── ai_services/       # Azure AI integration
│   └── templates/         # HTML templates
├── deploy/                # Deployment scripts
├── nginx/                 # Nginx configuration
├── docker-compose.yml     # Docker services definition
├── Dockerfile            # Application container
└── requirements.txt      # Python dependencies
```

## 🔧 Features

- **User Authentication**: Django Allauth integration
- **Document Processing**: Azure Document Intelligence
- **AI Chat**: OpenAI/Azure OpenAI integration
- **Speech Services**: Azure Speech Services
- **Real-time Updates**: WebSocket support
- **Background Tasks**: Celery integration
- **Admin Interface**: Django Admin
- **RESTful API**: Django REST Framework

## 🔒 Security

- HTTPS enforcement
- Security headers
- Rate limiting
- CSRF protection
- XSS protection
- SQL injection protection

## 📊 Monitoring

- Health check endpoint: `/health/`
- Application logs: `/opt/edusauti/logs/`
- Container monitoring: `./manage-prod.sh status`
- Automated monitoring: `./deploy/monitor.sh`

## 🔄 Backup & Recovery

- Automated daily backups
- Database and media file backup
- Easy restore process
- Backup retention policies

## 📚 Documentation

- [Deployment Guide](DEPLOYMENT.md) - Detailed deployment instructions
- [API Documentation](docs/api.md) - API endpoints and usage
- [Development Setup](docs/development.md) - Local development guide

## 🐛 Troubleshooting

1. **Check service status**: `./manage-prod.sh status`
2. **View logs**: `./manage-prod.sh logs [service]`
3. **Health check**: `./manage-prod.sh health`
4. **Restart services**: `./manage-prod.sh restart`

## 📞 Support

For deployment issues:
1. Check the logs
2. Review the deployment guide
3. Contact system administrator

## 🚀 Deployment Status

✅ **READY FOR DEPLOYMENT**

Your EduSauti application is now configured for production deployment on Ubuntu server with Docker containers.

**Next Steps:**
1. Transfer these files to your Ubuntu server (41.89.130.21)
2. Run the deployment scripts
3. Configure your domain DNS
4. Set up SSL certificates
5. Test the application

**Server Details:**
- IP: 41.89.130.21
- Domain: edusauti.ayubsoft-inc.systems
- Platform: Ubuntu + Docker + Nginx
- Database: PostgreSQL
- Cache: Redis
- Task Queue: Celery
