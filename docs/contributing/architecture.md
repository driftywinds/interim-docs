---
description: How interim's packages, SQLite schema, and upload state machine fit together.
---

# Architecture

interim is a single Go binary: an HTTP server that owns SQLite metadata and
talks to an S3-compatible bucket. It never proxies file bytes.

## Request flow at a glance

```text
POST /api/v1/uploads      reserve quota, pick staging key, sign PUT
PUT  <presigned>S3        browser writes the staging object
POST /api/v1/uploads/{id}/complete
                          HeadObject, size check, CopyObject, commit row
GET  /f/{id}              page with metadata and a download button
GET  /f/{id}/download     fresh signed GET or worker token, then redirect
```

Everything that survives a restart lives in SQLite. The object store holds only
file bytes and the staging objects the janitor cleans up.

## Example: one single-PUT upload

```text
1. POST /api/v1/uploads {"name":"report.pdf","size":2048000,"content_type":"application/pdf"}
   -> 201 {upload_id, url, upload_token, delete_token, ...}
   -> upload_intents row: state=pending, declared_size=2048000
   -> storage_reservations row: 2048000 bytes, expires with UPLOAD_URL_TTL

2. PUT <signed url>
   -> S3 writes files/uploads/<upload-id>

3. POST /api/v1/uploads/<id>/complete   X-Upload-Token: ...
   -> HeadObject: 2048000 bytes matches the reservation
   -> CopyObject files/uploads/<id> -> files/objects/<random>
   -> one transaction: files row + usage_totals update, intent state=completed

4. Best-effort delete of the staging key; the janitor removes leftovers.
```

If the client never completes, the reservation expires with the intent and the
janitor deletes the staging object. If completion is retried, it returns the
already-committed file instead of copying again.

## Packages

| Path | Responsibility |
| --- | --- |
| `cmd/interim` | Process entry point: load config, open SQLite, connect S3, start the server and janitor, handle graceful shutdown. |
| `internal/config` | Environment parsing and validation, including unit parsing and placeholder-secret rejection. |
| `internal/server` | HTTP surface: pages, API, admin, auth, middleware, rate limiting, and the janitor. |
| `internal/store` | SQLite access and schema migrations. |
| `internal/objects` | S3 client wrapper: presign, head, copy, list, multipart, delete. |
| `internal/download` | HMAC signer for Cloudflare Worker download tokens. |
| `internal/units` | Size and duration parsing shared by config and templates. |
| `web/` | Embedded server-rendered templates, static assets, and `openapi.yaml`. |
| `worker/` | Cloudflare Worker that streams private B2 objects for downloads. |

### `internal/server`

The HTTP layer is split by surface:

- `server.go` — router, middleware wiring, shared helpers, retention rules.
- `pages.go` — home, file, and download pages.
- `api.go` — `/api/v1/*` handlers.
- `openapi.go` — renders the embedded OpenAPI document, YAML, and HTML.
- `admin.go` — admin dashboard, bulk deletion, key management.
- `auth.go` — setup, login, logout, password change.
- `middleware.go` — request IDs, access logs, security headers, recovery.
- `ratelimit.go` — per-IP and per-account limiters.
- `cleanup.go` — janitor passes and orphan sweeps.

### `internal/objects`

`S3Store` wraps AWS SDK v2 with the compatibility tweaks interim needs:
path-style addressing, `when_required` checksums, a signing path that does not
send `Accept-Encoding`, and separate clients for the server-side and public
endpoints. Multipart calls use the server endpoint; part URLs use the public one.

### `internal/store`

SQLite is the single source of truth. The schema is embedded and applied at
startup, with additive migrations for columns that `CREATE TABLE IF NOT EXISTS`
cannot introduce.

| Table | Holds |
| --- | --- |
| `admin` | The single admin account and its bcrypt hash. |
| `sessions` | Session token hashes, CSRF tokens, absolute expiry, and last-seen time. |
| `api_keys` | User hashes (SHA-256), approval state, per-hash limits, and usage counters. |
| `files` | Live files: object key, size, expiry, delete-token hash, and retention snapshot. |
| `storage_reservations` | Held bytes per owner until an upload terminal state is reached. |
| `upload_intents` | Pending, completed, and aborted uploads, including multipart upload IDs and staging holds. |
| `upload_parts` | Reported multipart part ETags and sizes. |
| `usage_totals` | Fast counters for committed storage and file counts. |

## Concurrency model

- SQLite runs one logical writer, so a single instance owns a database. The
  reservation and intent state machines depend on that.
- Quota checks, reservations, and commits happen inside SQLite transactions, so
  two concurrent uploads cannot both believe they fit.
- Completion and abort are detached from the request deadline but bounded by
  `MAX_CONCURRENT_COMPLETIONS`; both are idempotent, so a retry is safe.
- The janitor claims rows before touching objects. A claim blocks a concurrent
  download-triggered extension, which is why a race cannot lose a file or leave
  a live row pointing at deleted bytes.

## Where to change things

| Change | Start here |
| --- | --- |
| New environment variable | `internal/config/config.go`, then the [configuration reference](../reference/configuration.md). |
| New API endpoint | `internal/server/api.go`, the router in `server.go`, and `web/openapi.yaml`. |
| New UI page | `web/templates/*.html` plus a handler in `internal/server/pages.go`. |
| Upload state machine | `internal/server/upload.go`, `internal/store/uploads.go`. |
| Retention or quota rules | `internal/server/server.go`, `internal/store/files.go`. |
| Storage provider behavior | `internal/objects/s3.go`. |

## Related pages

- [Development](development.md) — test and build commands.
- [Capacity and retention](../operations/capacity-and-retention.md) — the state
  machines in prose.
- [Security model](../operations/security.md) — the trust boundaries each
  package enforces.
