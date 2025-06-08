#!/bin/bash
set -e

# Function to run Django management commands
run_django_cmd() {
    echo "Running: python manage.py $@"
    python manage.py "$@"
}

# Wait for any dependencies (if needed)
echo "Starting Django application..."

# Run migrations
echo "Running database migrations..."
run_django_cmd migrate --noinput

# Collect static files
echo "Collecting static files..."
run_django_cmd collectstatic --noinput --clear

# Create superuser if environment variables are provided
if [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Creating superuser..."
    run_django_cmd shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='$DJANGO_SUPERUSER_EMAIL').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
"
fi

# Execute the main command
echo "Starting application with: $@"
exec "$@"