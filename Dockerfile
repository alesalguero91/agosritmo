# ---- Etapa de construcción ----
FROM python:3.10-slim as builder

WORKDIR /app
COPY requirements.txt .

# Instala dependencias de compilación (solo temporales)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && pip install --user -r requirements.txt \
    && apt-get remove -y gcc python3-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# ---- Etapa final ----
FROM python:3.10-slim

# 1. Instala Tesseract y dependencias esenciales (optimizado para Render)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    poppler-utils \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Copia las dependencias de Python instaladas
COPY --from=builder /root/.local /root/.local

# 3. Copia el proyecto
COPY . .

# 4. Configuración específica para Render
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV TESSERACT_CMD=/usr/bin/tesseract
ENV PORT=8000 

# 5. Permisos para scripts (si usas entrypoint.sh)
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 6. Puerto expuesto (Render lo redirige automáticamente)
EXPOSE $PORT

# 7. Comando de inicio optimizado para Render
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "--workers", "2", "app.wsgi:application"]

