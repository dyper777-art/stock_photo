#!/bin/bash

# Use Railway PORT if defined, otherwise default to 8000
PORT=${PORT:-8000}

# Apply migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start Gunicorn server
gunicorn myproject.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --threads 2


python manage.py migrate && gunicorn myproject.wsgi:application --bind 0.0.0.0:$PORT