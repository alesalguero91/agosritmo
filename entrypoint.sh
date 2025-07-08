#!/bin/bash
set -e

# Migraciones (si usas DB)
python manage.py migrate --noinput || echo "Migraciones fallidas, continuando..."

# Archivos estáticos
python manage.py collectstatic --noinput --clear || echo "Collectstatic fallido, continuando..."

# Inicia Gunicorn
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app.wsgi:application