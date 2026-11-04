FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN useradd -m -u 1000 user

COPY --chown=user backend/ ./backend/
COPY --chown=user frontend/ ./frontend/
COPY --chown=user database.rules.json ./

USER user

ENV HOST=0.0.0.0
ENV PORT=5500
ENV PYTHONUNBUFFERED=1

EXPOSE 5500

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5500/api/v1/auth/roles || exit 1

CMD ["python", "backend/main.py"]
