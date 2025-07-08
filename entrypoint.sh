#!/bin/bash
set -e

# Verifica la instalación de Django
python -c "import django; print(f'Django {django.__version__} está instalado')" || {
    echo "ERROR: Django no está instalado correctamente"
    exit 1
}

# Migraciones (opcional, solo si usas DB)
python manage.py migrate --noinput || echo "Advertencia: Falló migrate, continuando..."

# Archivos estáticos
python manage.py collectstatic --noinput --clear || echo "Advertencia: Falló collectstatic, continuando..."

# Inicia Gunicorn
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app.wsgi:application