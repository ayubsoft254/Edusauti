# Use Python 3.11 slim image
FROM python:3.11-slim-bookworm

# Upgrade system packages to reduce vulnerabilities
RUN apt-get update && apt-get upgrade -y && apt-get clean

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=core.settings.production

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /app/logs /app/staticfiles /app/media /app/data

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY src/ /app/

# Create a non-root user
RUN groupadd -r django && useradd -r -g django django

# Set proper ownership and permissions
RUN chown -R django:django /app && \
    chmod -R 755 /app

# Create entrypoint script
COPY <<EOF /app/entrypoint.sh
#!/bin/bash
set -e

# Function to run Django management commands
run_django_cmd() {
    echo "Running: python manage.py \$@"
    python manage.py "\$@"
}

# Wait for any dependencies (if needed)
echo "Starting Django application..."

# Run migrations
echo "Running database migrations..."
run_django_cmd migrate --noinput

# Collect static files
echo "Collecting static files..."
run_django_cmd collectstatic --noinput --clear

# Create superuser if needed (optional)
if [ "\$DJANGO_SUPERUSER_EMAIL" ] && [ "\$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Creating superuser..."
    run_django_cmd shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='\$DJANGO_SUPERUSER_EMAIL').exists():
    User.objects.create_superuser('\$DJANGO_SUPERUSER_EMAIL', '\$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
"
fi

# Execute the main command
echo "Starting application with: \$@"
exec "\$@"
EOF

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh && chown django:django /app/entrypoint.sh

# Switch to non-root user
USER django

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:3000", "--workers", "3", "--worker-class", "uvicorn.workers.UvicornWorker", "core.asgi:application"]