#!/usr/bin/env bash
set -o errexit

# Instala Tesseract (requiere comunidad Render)
apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instala dependencias Python
pip install -r requirements.txt

# Colecta archivos estáticos
python manage.py collectstatic --no-input