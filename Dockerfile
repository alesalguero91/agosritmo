# ---- Builder Stage ----
FROM python:3.10-slim as builder

WORKDIR /app
COPY requirements.txt .

# Instala dependencias del sistema y Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && pip install --user --no-warn-script-location -r requirements.txt \
    && apt-get remove -y gcc python3-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# ---- Runtime Stage ----
FROM python:3.10-slim

# Instala dependencias del sistema (Tesseract y otros)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    poppler-utils \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia dependencias de Python
COPY --from=builder /root/.local /usr/local
COPY . .

# Configura entorno
ENV PATH=/usr/local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV TESSERACT_CMD=/usr/bin/tesseract
ENV PORT=8000

# Asegura que entrypoint.sh sea ejecutable
RUN chmod +x /app/entrypoint.sh

EXPOSE $PORT

ENTRYPOINT ["/app/entrypoint.sh"]