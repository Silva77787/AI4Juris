#!/bin/sh

# Apply database migrations before starting the server
python manage.py migrate

# Execute the provided command (e.g., runserver)
exec "$@"
