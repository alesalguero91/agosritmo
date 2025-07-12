#!/bin/bash
set -e

# Verificación de dependencias
python -c "
import sys
try:
    import django, rest_framework
    print(f'✓ Django {django.__version__} y DRF {rest_framework.__version__} instalados', file=sys.stderr)
except ImportError as e:
    print(f'✗ Error de importación: {e}', file=sys.stderr)
    exit(1)
"

# Migraciones (si usas base de datos)
python manage.py migrate --noinput || echo "⚠ Advertencia: Falló migrate" >&2

# Archivos estáticos
python manage.py collectstatic --noinput --clear || echo "⚠ Advertencia: Falló collectstatic" >&2

# Inicio de Gunicorn (ajustado para tu estructura)
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 titanio.wsgi:application