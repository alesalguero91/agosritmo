FROM python:3.10-slim

WORKDIR /app

# Instala dependencias del sistema
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
ENV PORT=8000
ENV TESSERACT_CMD=/usr/bin/tesseract
ENV PYTHONPATH=/app

EXPOSE $PORT

CMD ["gunicorn", "titanio.wsgi:application", "--bind", "0.0.0.0:8000"]