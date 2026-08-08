# Local Docker Compose

This setup starts MySQL, Redis, FastAPI, and Celery with ClamAV installed inside
the Celery image.

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

## Logs

```powershell
docker compose logs -f backend celery
```

The first Celery start can take longer because `freshclam` downloads antivirus
definitions. The definitions are retained in the `grd-clamav-data` volume.

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
Compose-managed Redis and ClamAV volumes. The external MySQL volume should
always be backed up separately.
