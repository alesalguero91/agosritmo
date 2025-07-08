# ---- Builder Stage ----
FROM python:3.10-slim as builder

WORKDIR /app
COPY requirements.txt .

# Instala dependencias como usuario no-root
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    python -m pip install --user --no-warn-script-location -r requirements.txt && \
    apt-get remove -y gcc python3-dev && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# ---- Runtime Stage ----
FROM python:3.10-slim

# Instala dependencias del sistema como root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    poppler-utils \
    ghostscript && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia dependencias como usuario no-root
COPY --from=builder /root/.local /home/appuser/.local
COPY . .

# Crea usuario no-root y configura permisos
RUN useradd -m appuser && \
    chown -R appuser:appuser /app && \
    chmod +x /app/entrypoint.sh

# Configura entorno
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV TESSERACT_CMD=/usr/bin/tesseract
ENV PORT=8000

USER appuser

EXPOSE $PORT

# Usa exec para mejor manejo de señales
ENTRYPOINT ["/app/entrypoint.sh"]