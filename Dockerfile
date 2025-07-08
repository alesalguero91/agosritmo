# Builder stage
FROM python:3.10-slim as builder

WORKDIR /app
COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && pip install --user --no-warn-script-location -r requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Runtime stage
FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    poppler-utils \
    ghostscript \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV TESSERACT_CMD=/usr/bin/tesseract
ENV PORT=8000

RUN chmod +x /app/entrypoint.sh

EXPOSE $PORT
ENTRYPOINT ["/app/entrypoint.sh"]