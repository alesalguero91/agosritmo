#!/bin/bash
set -e

# Verificación rápida de dependencias
python -c "import django; print(f'✓ Django {django.__version__} está instalado')"

# Recoge archivos estáticos (obligatorio en producción)
python manage.py collectstatic --noinput --clear

# Inicia Gunicorn con configuración optimizada
exec gunicorn --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --max-requests 1000 \
    titanio.wsgi:application