---
description: Run interim with Docker, create the first admin, and pick a storage route.
---

# Quick start

interim is a Go service with SQLite metadata and an S3-compatible object store.
Docker is the primary deployment target; the binary can also run directly.

## Prerequisites

- A reachable S3-compatible bucket: AWS S3, MinIO, Cloudflare R2, Backblaze B2,
  Wasabi, sss3, or similar. The bucket stays private.
- Docker with Compose, or Go 1.27+ for a direct build.
- A public HTTPS origin for the web UI. Everything else can stay internal.

!!! note "The bucket must allow browser PUTs"

    Direct uploads go from the browser to storage, so the bucket needs a CORS
    policy for the interim origin. The exact policy and provider notes are in
    [S3-compatible storage](../guides/s3-compatible-storage.md).

## Run with Docker

```sh
git clone https://github.com/driftywinds/interim.git
cd interim
cp .env.example .env
# edit PUBLIC_BASE_URL, S3_* and capacity limits
docker compose up --build
```

The Compose file binds the Go listener to `127.0.0.1:8080`. Put Caddy,
cloudflared, or another trusted proxy in front of it for public access. When you
do, set `TRUST_PROXY=true` and `TRUSTED_PROXY_CIDRS` to that proxy's source
range; otherwise all per-IP limits collapse into one global bucket. See
[Deployment notes](../operations/deployment.md).

The minimum you should set in `.env`:

```dotenv
PUBLIC_BASE_URL=https://files.example.com
S3_ENDPOINT=https://s3.us-west-004.backblazeb2.com   # empty for AWS S3
S3_PUBLIC_ENDPOINT=https://s3.us-west-004.backblazeb2.com
S3_REGION=us-west-004
S3_BUCKET=interim
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
MAX_FILE_SIZE=5GB
MAX_STORAGE=20GB
RETENTION=7d
```

Placeholder credentials such as `change-me` or `replace-with-*` are rejected at
startup. Generate secrets with `openssl rand -base64 48`.

## Create the first admin

Open `http://localhost:8080/setup` and enter the one-time setup token:

```sh
docker exec interim cat /data/setup_token
```

Alternatively, set `SETUP_TOKEN` in `.env` before starting. The setup page is
only available while no admin exists, and the generated token file is deleted
after successful setup.

!!! warning "Keep the setup token private"

    The token is the only thing that stops a scanner from claiming a fresh
    instance. The `/setup` route closes as soon as the admin account exists.

## Data and backups

The SQLite database, generated session secret, and WAL files live in the
`interim-data` volume at `/data`. Back up the volume, not individual files while
the container is running. Only S3 holds file bytes; SQLite holds the mapping,
expiry, delete-token hashes, sessions, quotas, upload intents, setup state, and
admin credentials.

## Run without Docker

```sh
cp .env.example .env
go run ./cmd/interim
```

Or build a static binary and run it:

```sh
CGO_ENABLED=0 go build -trimpath -o bin/interim ./cmd/interim
./bin/interim
```

`DATA_DIR` defaults to `./data`. See [Development](../contributing/development.md)
for the test and vet commands.

## Choose a storage route

| Route | Use it when |
| --- | --- |
| [S3-compatible storage](../guides/s3-compatible-storage.md) | You have AWS S3, MinIO, R2, B2, Wasabi, or another S3 endpoint that browsers can reach. |
| [sss3 with Cloudflare and Caddy](../guides/sss3-cloudflare.md) | You run sss3 behind a Cloudflare Tunnel and keep uploads under Cloudflare's ~100 MB request-body cap. |
| [Tailscale-only sss3](../guides/tailscale-sss3.md) | sss3 is on a home machine behind CGNAT and you need uploads larger than Cloudflare allows. |
| [B2 private bucket with Cloudflare Worker](../guides/b2-worker.md) | You want B2's free Cloudflare egress with private, expiring downloads. |

[Choosing a storage route](storage-routes.md) compares them side by side.

## Check the instance

```sh
# health of the database and storage connection
curl -fsS http://localhost:8080/healthz

# capacity, retention, and whether uploads are accepted
curl -s http://localhost:8080/api/v1/status | jq .
```

```json
{
  "accepting_uploads": true,
  "public_uploads": true,
  "storage": {
    "files": 3,
    "used_bytes": 8589934592,
    "reserved_bytes": 0,
    "limit_bytes": 21474836480,
    "available_bytes": 12884901888,
    "used_percent": 40,
    "unlimited": false
  },
  "retention_seconds": 604800,
  "retention_human": "7 days",
  "retention_extend_on_download": false,
  "max_file_size_bytes": 5368709120,
  "download_url_ttl_seconds": 300,
  "server_time": "2026-01-01T12:00:00Z"
}
```

The home page shows storage usage and the current retention rule. Upload a small
file through the UI, then download it from the file page.

!!! tip "If the upload fails"

    Check the bucket CORS policy first; it is the most common misconfiguration.
    A browser console error naming the S3 origin means `S3_PUBLIC_ENDPOINT` and
    the bucket CORS `AllowedOrigins` do not match `PUBLIC_BASE_URL`. See
    [S3-compatible storage](../guides/s3-compatible-storage.md#required-bucket-cors).

## Next steps

- [Configuration](../reference/configuration.md) — every environment variable.
- [Web UI](../usage/web-ui.md) — uploads, browser history, and restricted mode.
- [API](../usage/api.md) — the same flow from scripts and curl.
- [Capacity and retention](../operations/capacity-and-retention.md) — quotas,
  expiry, and the janitor.
