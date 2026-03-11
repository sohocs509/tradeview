FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY inference.py .
COPY training.py .

RUN mkdir -p /data/models

ENV TV_ML_PORT=8766

EXPOSE 8766

CMD ["python", "inference.py"]
