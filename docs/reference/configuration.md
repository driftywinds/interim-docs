---
description: Every interim environment variable, with defaults, ranges, and validation rules.
---

# Configuration

All runtime configuration is read from the environment. `.env` is loaded
automatically for local runs, and Compose uses it via `env_file`. See
[`.env.example`](https://github.com/driftywinds/interim/blob/main/.env.example)
for commented defaults.

## Minimal example

Copy `.env.example` to `.env` and set at least these values:

```dotenv
PUBLIC_BASE_URL=https://files.example.com

S3_ENDPOINT=https://s3.us-west-004.backblazeb2.com
S3_PUBLIC_ENDPOINT=https://s3.us-west-004.backblazeb2.com
S3_REGION=us-west-004
S3_BUCKET=interim
S3_ACCESS_KEY=your-key-id
S3_SECRET_KEY=your-application-key

MAX_STORAGE=20GB
MAX_FILE_SIZE=5GB
RETENTION=7d
```

Everything else has a default. The instance refuses to start on a value it can
validate and reject, such as a placeholder secret, a malformed CIDR, or
`UPLOAD_INTENT_TTL` shorter than `UPLOAD_URL_TTL`.

## Value syntax

| Kind | Accepted | Examples |
| --- | --- | --- |
| Duration | Days or Go durations | `7d`, `1.5d`, `36h`, `90m`, `45s` |
| Size | Binary units, case-insensitive | `5GB`, `512MB`, `20GB`, `1024KB` |
| Boolean | `true` / `false` | `TRUST_PROXY=true` |
| List | Comma- or space-separated | `TRUSTED_PROXY_CIDRS=127.0.0.1/32,::1/128` |
| CIDR list | IPs or CIDRs | `10.0.0.0/8`, `192.168.1.10` |

`MAX_STORAGE` also accepts `0` or `unlimited` to disable the global cap.
`MAX_FILES=0` disables the file-count cap.

## Core

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `PUBLIC_BASE_URL` | yes | — | Public origin used in links and API examples. No trailing slash or path prefix. |
| `LISTEN_ADDR` | no | `:8080` | HTTP listen address. |
| `DATA_DIR` | no | `./data` | Directory for SQLite and generated files. Compose overrides this to `/data` inside the container. |
| `DATABASE_PATH` | no | `DATA_DIR/interim.db` | Explicit SQLite path. |
| `SESSION_SECRET` | no | auto-generated | At least 32 chars. If absent, a 0600 secret is generated in `DATA_DIR`. |
| `SETUP_TOKEN` | no | auto-generated | One-time token required to create the first admin. At least 32 chars. If absent, `DATA_DIR/setup_token` is generated (0600) and deleted after setup. |
| `COOKIE_SECURE` | no | `auto` | `auto` follows the scheme of `PUBLIC_BASE_URL`. `__Host-` cookie names are used when secure. |
| `LOG_LEVEL` | no | `info` | `debug`, `info`, `warn`, `error`. |
| `CONTACT_EMAIL` | no | — | Optional contact address shown on the restricted-upload page. |
| `DONATION_URL` | no | — | Optional https support link shown on the home page. |

## Reverse proxy and client IPs

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `TRUST_PROXY` | no | `false` | Trust forwarded headers from peers in `TRUSTED_PROXY_CIDRS`. |
| `TRUSTED_PROXY_CIDRS` | with `TRUST_PROXY` | — | Comma/space-separated proxy CIDRs or IPs. Required and validated when `TRUST_PROXY=true`. |
| `TRUSTED_CLIENT_IP_HEADER` | no | — | Optional header carrying the real client IP (for example `CF-Connecting-IP`). Only read when the peer is in `TRUSTED_PROXY_CIDRS`; requires `TRUST_PROXY=true`. `Forwarded`, `X-Forwarded-For`, and `X-Real-IP` are rejected. |

!!! warning "Limits collapse without `TRUST_PROXY`"

    Behind Caddy or cloudflared with `TRUST_PROXY=false`, every request appears
    to come from the proxy. Per-IP login, upload, key-creation, and download
    limits become global, and one failed-login burst can lock out the admin.

## Admin sessions

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `ADMIN_SESSION_TTL` | no | `12h` | Absolute session lifetime, 15m–168h. |
| `ADMIN_IDLE_TIMEOUT` | no | `2h` | Revoke an admin session after this much inactivity, 5m–168h. |

## S3-compatible storage

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `S3_ENDPOINT` | AWS no | — | Include scheme. Leave empty for AWS S3. Used for server-side Head/Copy/List/Delete. |
| `S3_PUBLIC_ENDPOINT` | no | `S3_ENDPOINT` | Endpoint embedded in presigned URLs; must be browser-reachable. |
| `S3_REGION` | no | `us-east-1` | Any non-empty value for servers that ignore regions. |
| `S3_BUCKET` | yes | — | Must be a bare bucket name. |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | AWS no | — | Leave both empty to use the instance-role/default credential chain. Placeholder values such as `change-me` or `replace-with-*` are rejected. |
| `S3_PUT_ACCESS_KEY` / `S3_PUT_SECRET_KEY` | no | — | Optional write-only identity used only for presigned browser PUTs. Required for multipart unless the next flag is set. |
| `S3_PUBLIC_ENDPOINT_BLOCKS_COPY` | no | `false` | Operator assertion that the public endpoint strips every `X-Amz-*` request header. It is trusted, not verified; prefer `S3_PUT_ACCESS_KEY`/`S3_PUT_SECRET_KEY`. Requires a public endpoint distinct from `S3_ENDPOINT`. |
| `S3_FORCE_PATH_STYLE` | no | `true` | Keep true for sss3/MinIO/Garage; false for AWS. |
| `S3_AUTO_CREATE_BUCKET` | no | `false` | Attempts `CreateBucket` if missing. Prefer pre-creating it. |
| `S3_OBJECT_PREFIX` | no | `files` | Key prefix; normalized with a trailing `/`. |

## Upload access

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `PUBLIC_UPLOADS_ENABLED` | no | `true` | `false` restricts upload intents to admin-approved user hashes and disables public hash creation. Existing hashes start unapproved. |

## Uploads and multipart

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `UPLOAD_URL_TTL` | no | `30m` | Presigned PUT / part URL lifetime. 5m–2h. A completed/aborted single-PUT reservation is held until this deadline. |
| `UPLOAD_INTENT_TTL` | no | `45m` | Deadline for completion; must be at least `UPLOAD_URL_TTL`. Max 6h. |
| `MULTIPART_UPLOAD_ENABLED` | no | `false` | Enable S3 multipart uploads for files above `MULTIPART_THRESHOLD`. |
| `MULTIPART_THRESHOLD` | no | `64MB` | Size above which multipart is used. `0` makes every upload multipart. Max 5GB. |
| `MULTIPART_PART_SIZE` | no | `16MB` | Requested part size. 5MB–5GB; raised automatically for the 10,000-part limit. |
| `MULTIPART_CONCURRENCY` | no | `3` | Browser part parallelism, 1–8. |
| `MULTIPART_SIGN_PART_LENGTH` | no | `true` | Sign the exact part Content-Length into presigned URLs. Disable only if the provider cannot verify signed Content-Length. |
| `MAX_PENDING_UPLOADS_PER_CLIENT` | no | `2` | Pending intent cap per approved hash or per client network. `0` disables. Unapproved/self-service hashes share the per-IP bucket. |
| `MAX_RESERVED_BYTES_PER_CLIENT` | no | `MAX_FILE_SIZE` | Reserved-byte cap per approved hash or per client network. `0` disables. A per-hash file-size grant can raise this for that hash. |
| `MAX_CONCURRENT_COMPLETIONS` | no | `8` | Upper bound on detached upload finalizations, 1–256. |

## Capacity and retention

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `MAX_STORAGE` | no | `20GB` | Hard total cap, binary units. Set to `0` or `unlimited` to disable the global cap. |
| `MAX_FILE_SIZE` | no | `5GB` | Default per-file cap for anonymous/self-service uploads and new hashes. An admin can override it per hash; provider limits still apply. Cannot exceed `MAX_STORAGE` when a cap is set. Files above 5GB require multipart uploads. |
| `MAX_FILES` | no | `100000` | Global committed-file count cap. `0` disables. |
| `RETENTION` | no | `7d` | File lifetime. Supports `7d`, `30d`, `1.5d`, or Go durations like `12h`. 1h–3650d. Existing files keep their original expiry until their next download when sliding retention is enabled. |
| `RETENTION_EXTEND_ON_DOWNLOAD` | no | `false` | Slide retention from the last download: each download-link request moves the file expiry to `now + RETENTION`. Downloads bypass interim, so the extension is triggered when the link is issued. |
| `DOWNLOAD_URL_TTL` | no | `5m` | 30s–1h. Also the worker download token lifetime. |

## Worker-backed downloads

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `DOWNLOAD_WORKER_ENABLED` | no | `false` | Use Cloudflare Worker download URLs instead of presigned S3 GETs. |
| `DOWNLOAD_WORKER_URLS` | worker mode yes | — | Comma/space-separated HTTPS worker base URLs. The `/d/<token>` path is appended. |
| `DOWNLOAD_WORKER_SECRET` | worker mode yes | — | At least 32 characters; must match the worker's `DOWNLOAD_TOKEN_SECRET`. Placeholder values are rejected. |

See [B2 with a Cloudflare Worker](../guides/b2-worker.md) for the deployment.

## Maintenance

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `SWEEP_ON_STARTUP` | no | `false` | Delete unknown objects under `S3_OBJECT_PREFIX` at startup. Leave false unless the prefix is dedicated to this database. |

## Example: locked-down private instance

```dotenv
PUBLIC_BASE_URL=https://files.example.com
PUBLIC_UPLOADS_ENABLED=false
CONTACT_EMAIL=admin@example.com

MAX_STORAGE=100GB
MAX_FILE_SIZE=2GB
MAX_FILES=10000
RETENTION=30d
RETENTION_EXTEND_ON_DOWNLOAD=false

TRUST_PROXY=true
TRUSTED_PROXY_CIDRS=127.0.0.1/32,::1/128
TRUSTED_CLIENT_IP_HEADER=CF-Connecting-IP
```

What changes:

- `POST /api/v1/keys` is disabled; only hashes created in `/admin` exist.
- Existing hashes start unapproved and cannot upload until approved.
- Anonymous uploads return `401 uploads_restricted`.
- `CONTACT_EMAIL` is shown on the restricted-upload page so people can ask for
  access.

## Example: large-file instance

```dotenv
MAX_FILE_SIZE=50GB
MULTIPART_UPLOAD_ENABLED=true
MULTIPART_THRESHOLD=64MB
MULTIPART_PART_SIZE=64MB
MULTIPART_CONCURRENCY=3
UPLOAD_URL_TTL=2h
UPLOAD_INTENT_TTL=3h
MAX_STORAGE=500GB
```

Multipart becomes mandatory above the provider's single-PUT limit, so the part
size has to stay below both the provider maximum and any proxy body cap. See
[Capacity and retention](../operations/capacity-and-retention.md#multipart-uploads)
for the part-size rules.

## Example: Worker-backed downloads

```dotenv
DOWNLOAD_WORKER_ENABLED=true
DOWNLOAD_WORKER_URLS=https://dl1.example.com,https://dl2.example.com
DOWNLOAD_WORKER_SECRET=<same value as the worker's DOWNLOAD_TOKEN_SECRET>
DOWNLOAD_URL_TTL=2m
```

[`GET /api/v1/status`](../usage/api.md#endpoints) reports the effective
retention, file-size limit, and whether the instance accepts uploads, which is a
quick way to check that a change took effect.

## Per-hash limits

User hashes carry two optional overrides, edited in `/admin`:

- **Max file size** defaults to `MAX_FILE_SIZE`; `0` means unlimited for that
  hash. The S3 single-PUT limit (5 GB) or multipart object limit (5 TiB) and
  `MAX_STORAGE` still apply.
- **Retention** defaults to `RETENTION`; `0` means the hash's files never expire.
  A positive value is captured when the upload is committed, so changing the
  hash later does not rewrite existing files.

Hashes created before this feature inherit the current instance defaults. New
hashes are created with the instance defaults filled in, and the admin can edit
either value. Self-service hashes created through `POST /api/v1/keys` always
receive the instance defaults.

## Related pages

- [S3-compatible storage](../guides/s3-compatible-storage.md) — endpoint details
  and provider-specific settings.
- [B2 with a Cloudflare Worker](../guides/b2-worker.md) — Worker-backed
  downloads.
- [Capacity and retention](../operations/capacity-and-retention.md) — quota and
  expiry behavior.
