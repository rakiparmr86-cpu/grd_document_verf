#!/bin/sh
set -eu

mkdir -p /app/storage/quarantine /var/lib/clamav
chown -R grd:grd /app/storage/quarantine

echo "Updating ClamAV virus definitions..."
if ! freshclam; then
    echo "WARNING: ClamAV definitions could not be updated; scans will fail closed if no usable definitions exist."
fi

echo "Starting Celery worker with local ClamAV scanning..."
exec gosu grd python -m celery \
    -A app.workers.celery_app.celery_app \
    worker \
    --loglevel=info \
    --concurrency=2
