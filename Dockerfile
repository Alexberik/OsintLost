FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/
COPY scripts/ scripts/
COPY models/ models/

RUN bash scripts/download_model.sh || true

ENV PORT=8090
EXPOSE 8090

CMD ["python", "backend/server.py"]
