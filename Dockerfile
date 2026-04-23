FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY uv.loc[k] ./

RUN pip install --no-cache-dir .

COPY app ./app
COPY scripts ./scripts

RUN mkdir -p /data
ENV DATABASE_PATH=/data/bet.db

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
