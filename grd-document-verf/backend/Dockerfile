# syntax=docker/dockerfile:1

FROM python:3.11-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app/backend

RUN groupadd --system grd \
    && useradd --system --gid grd --home-dir /app --shell /usr/sbin/nologin grd

COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install --requirement requirements.txt

COPY app ./app
COPY run.py ./run.py

RUN mkdir -p /app/storage/quarantine /app/celerybeat \
    && chown -R grd:grd /app

FROM base AS api

USER grd
EXPOSE 8003

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]

FROM base AS worker

USER root

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        clamav \
        clamav-freshclam \
        gosu \
    && rm -rf /var/lib/apt/lists/*

COPY docker/celery-entrypoint.sh /usr/local/bin/celery-entrypoint
RUN sed -i 's/\r$//' /usr/local/bin/celery-entrypoint \
    && chmod 0755 /usr/local/bin/celery-entrypoint

ENTRYPOINT ["celery-entrypoint"]
