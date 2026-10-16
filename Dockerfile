FROM python:3.10-slim

WORKDIR /app

# Instala dependencias del sistema (Tesseract y herramientas PDF)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    poppler-utils \
    ghostscript \
    libmagic1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Instala dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia la aplicación
COPY . .

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV TESSERACT_CMD=/usr/bin/tesseract

# Ejecuta Gunicorn: usa el puerto $PORT de Render, 1 worker (CPU limitada) y timeout amplio para el OCR
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 300 --max-requests 1000 titanio.wsgi:application