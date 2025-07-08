# Builder stage
FROM python:3.10-slim as builder

WORKDIR /app
COPY requirements.txt .

# Instalación separada en pasos para mejor diagnóstico
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev

RUN pip install --no-cache-dir --user -r requirements.txt

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Runtime stage
FROM python:3.10-slim

# Dependencias de sistema para Tesseract y Django
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    poppler-utils \
    ghostscript \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia dependencias Python desde builder
COPY --from=builder /root/.local /usr/local
COPY . .

# Configuración de entorno
ENV PATH=/usr/local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV TESSERACT_CMD=/usr/bin/tesseract
ENV PORT=8000
ENV PYTHONPATH=/app

# Permisos para entrypoint
RUN chmod +x /app/entrypoint.sh

EXPOSE $PORT
ENTRYPOINT ["/app/entrypoint.sh"]