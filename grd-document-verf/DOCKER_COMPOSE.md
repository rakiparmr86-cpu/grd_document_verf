# Local Docker Compose

This setup starts MySQL, Redis, MinIO, FastAPI, Celery with ClamAV, and Celery
Beat for scheduled retention cleanup.

## Existing local containers

The manually-created `grd-mysql` and `grd-redis` containers publish the same
ports as Compose. Stop them before starting the Compose stack:

```powershell
docker stop grd-mysql grd-redis
```

Do not delete the `grd-mysql-data` volume. Compose intentionally reuses it.

## Start

From the project root:

```powershell
docker compose up -d --build
docker compose ps
```

The API is available at `http://127.0.0.1:8003`, and API documentation is at
`http://127.0.0.1:8003/docs`.

The MinIO S3 API is available at `http://127.0.0.1:9000`, and its management
console is at `http://127.0.0.1:9001`. Change `MINIO_ROOT_USER` and
`MINIO_ROOT_PASSWORD` before any shared or production deployment.

## Logs

```powershell
docker compose logs -f backend celery celery-beat minio
```

The first Celery start can take longer because `freshclam` downloads antivirus
definitions. The definitions are retained in the `grd-clamav-data` volume.

## Document storage

Local F5 development uses `STORAGE_BACKEND=local` from `backend/.env`. Compose
overrides it with `STORAGE_BACKEND=minio`, so backend and Celery share private
objects through the `grd-quarantine` bucket instead of a host folder.

For production, point `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, and
`MINIO_SECRET_KEY` at the managed or redundant MinIO deployment. The bundled
single-node MinIO service is intended for local integration testing.

## Retention cleanup

Celery Beat sends `expire_quarantined_documents` every hour. The worker deletes
file content older than `DOCUMENT_RETENTION_DAYS` (30 by default) from local or
MinIO storage and records `storage_deleted_at` in MySQL. The document metadata
is retained for audit purposes. Configure the schedule with:

- `DOCUMENT_EXPIRY_ENABLED`
- `DOCUMENT_RETENTION_DAYS`
- `DOCUMENT_EXPIRY_SWEEP_SECONDS`
- `DOCUMENT_EXPIRY_BATCH_SIZE`

The document lifecycle reported by the API is:

`UPLOADED -> QUARANTINED -> SCANNING -> PROCESSING -> COMPLETED / MANUAL_REVIEW / FAILED`

## Rate limiting

FastAPI uses Redis for per-user and per-tenant request counters. The active
limits are configured in `backend/.env` with the `API_RATE_LIMIT_*`,
`UPLOAD_RATE_LIMIT_*`, and `LOGIN_RATE_LIMIT_*` settings. Exceeded limits return
HTTP `429` with `Retry-After` and `X-RateLimit-*` response headers.

Rate limiting is configured to fail closed: if Redis is unavailable, protected
requests return HTTP `503` instead of bypassing the control.

## Stop

```powershell
docker compose down
```

Do not use `docker compose down -v` unless you intentionally want to remove
Compose-managed Redis, MinIO, Celery Beat, and ClamAV volumes. The external
MySQL volume and production MinIO data should always be backed up separately.
