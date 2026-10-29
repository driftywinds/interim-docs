---
description: TLS, reverse proxies, SQLite, backups, and production constraints for interim.
---

# Deployment notes

## Public origin and TLS

- Put interim behind a TLS-terminating reverse proxy and set
  `PUBLIC_BASE_URL` to the HTTPS origin.
- The checked-in Compose file binds the Go listener to `127.0.0.1:8080`; keep it
  off public interfaces. If the proxy is another container, attach it to the
  Compose network instead of publishing the app port publicly.

## Trusted proxy

- Set `TRUST_PROXY=true` only behind a proxy you control, and list the proxy
  source addresses in `TRUSTED_PROXY_CIDRS` (for example
  `127.0.0.1/32,::1/128`). Forwarded headers from other peers are ignored.
- If you leave `TRUST_PROXY=false` behind Caddy/cloudflared, every request
  appears to come from the proxy: per-IP login, upload, key-creation and download
  limits become global, and one failed-login burst can lock out the admin.
- If your frontend/proxy overwrites `X-Forwarded-For` with its own address but
  preserves `CF-Connecting-IP` (some proxies do), set
  `TRUSTED_CLIENT_IP_HEADER=CF-Connecting-IP` alongside `TRUST_PROXY=true` and
  `TRUSTED_PROXY_CIDRS`. The header is only read from a trusted proxy peer.

## Secrets

- Keep the one-time `SETUP_TOKEN` (or `DATA_DIR/setup_token`) private. The file
  is removed after the first admin is created.
- Generate real values with `openssl rand -base64 48`; the loader rejects the
  `.env.example` placeholder strings and known placeholder S3 credentials.
- Rotate the sss3/B2/Cloudflare credentials before deployment and keep `.env`
  out of version control.

## Bucket and CORS

- The S3 bucket must be browser-reachable at `S3_PUBLIC_ENDPOINT`, with the CORS
  policy in [S3-compatible storage](../guides/s3-compatible-storage.md). The
  bucket itself stays private; only presigned PUTs and short-lived download URLs
  are exposed.
- Server-side `HeadObject`, `CopyObject`, `ListObjectsV2`, and delete calls use
  `S3_ENDPOINT`. On sss3 with the public CopyObject block, this endpoint must be
  internal or otherwise exempt from that block.
- Keep the bucket private. Do not enable public ACLs or public bucket policies.

## Example: Caddy in front of Compose

The Compose file binds interim to `127.0.0.1:8080`, so a host-installed Caddy
can terminate TLS and proxy to it:

```caddyfile
files.example.com {
    encode zstd gzip
    reverse_proxy 127.0.0.1:8080
}
```

Caddy connects from `127.0.0.1`, so this matches:

```dotenv
PUBLIC_BASE_URL=https://files.example.com
TRUST_PROXY=true
TRUSTED_PROXY_CIDRS=127.0.0.1/32,::1/128
```

If cloudflared runs in front of Caddy, add `TRUSTED_CLIENT_IP_HEADER=CF-Connecting-IP`
and include the cloudflared source range in `TRUSTED_PROXY_CIDRS`.

## Example: proxy on the Compose network

When the proxy is another container, do not publish the app port. Attach both
services to an internal network and proxy to the service name:

```yaml
services:
  interim:
    build: .
    env_file: .env
    environment:
      DATA_DIR: /data
    volumes:
      - interim-data:/data
    networks: [internal]

  caddy:
    image: caddy:2
    depends_on: [interim]
    ports: ["443:443", "80:80"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
    networks: [internal]

networks:
  internal:

volumes:
  interim-data:
  caddy-data:
```

```caddyfile
files.example.com {
    reverse_proxy interim:8080
}
```

Then set `TRUSTED_PROXY_CIDRS` to the proxy container's subnet (for example
`172.18.0.0/16`) and keep `S3_ENDPOINT` on the same network.

## Example: backup and restore

SQLite is the only stateful thing in the container. Back up the volume while
the service is stopped, or use SQLite's online backup, so the WAL is consistent:

```sh
docker compose stop interim

docker run --rm \
  -v interim-data:/data \
  -v "$PWD":/backup \
  alpine tar czf "/backup/interim-data-$(date +%F).tar.gz" -C /data .

docker compose start interim
```

Restore into a fresh volume:

```sh
docker compose down

docker run --rm \
  -v interim-data:/data \
  -v "$PWD":/backup \
  alpine sh -c 'rm -rf /data/* && tar xzf /backup/interim-data-YYYY-MM-DD.tar.gz -C /data'

docker compose up -d
```

Restoring an old database against a bucket that kept receiving uploads makes the
new objects orphans, which the janitor may remove. Restore the matching bucket
state, or keep `SWEEP_ON_STARTUP=false` and let only the guarded runtime sweep
run.

## Example: health check

```sh
curl -fsS https://files.example.com/healthz
curl -fsS https://files.example.com/api/v1/status | jq .accepting_uploads
```

`/healthz` only reveals database and storage detail to a loopback caller. Point
an external monitor at the status endpoint instead.

## Data, SQLite, and backups

- Run one instance per SQLite database. The reservation and intent state
  machines rely on SQLite's single-writer behaviour.
- Keep `DATA_DIR` (SQLite/session secret) separate from the sss3 data directory.
  Never point both at `./data`; the object store must not be able to overwrite
  the database or secret files.
- Back up the `/data` volume. Only S3 holds file bytes; SQLite holds the mapping,
  expiry, delete-token hashes, sessions, quotas, upload intents, setup state,
  and admin credentials.

## Object prefix hygiene

- Use a dedicated bucket and `S3_OBJECT_PREFIX`. The janitor treats objects
  under that prefix as interim-owned and deletes ones with no matching file or
  live intent.
- The startup sweep is disabled by default; runtime sweeps still run after a
  15-minute grace period and refuse to act if the database knows no objects or
  most listed objects are unknown.
- Never share the prefix with another instance, a test environment, or unrelated
  data.

## Container hardening

The Docker example uses a read-only root filesystem, a writable `/data` volume,
and a non-root user, plus:

- `no-new-privileges:true`
- `cap_drop: ALL`
- a 64 MB `tmpfs` at `/tmp`
- a 150 s stop grace period, matched by the app's two-minute graceful shutdown

## Timeouts and completion

The HTTP server uses 10 s header, 30 s read, 30 s write, and 60 s idle timeouts.
File bytes go directly to S3, so these do not constrain large uploads.

Completion detaches from the request context and clears the per-response write
deadline, with a 30-minute background deadline. A proxy can still time out
before the response arrives; completion is idempotent, so retrying it is safe.

## Static asset caching

HTML references static assets with a content hash (`app.js?v=...`). A new build
gets new asset URLs, so Cloudflare/browser caches cannot serve an old JavaScript
client after a deploy. Static assets are immutable-cached under those versioned
URLs; rebuild the image to regenerate the hash.

## Sizing

A single PUT temporarily needs space for both the staging object and the live
copy. Multipart uses the staging key as the live object and avoids that second
copy. Size `MAX_STORAGE` with that in mind.

## Supply chain

For production, pin container images by digest (especially the sss3 image, which
holds the data and RW credential) and pin GitHub Actions to commit SHAs rather
than mutable major tags.

## Worker downloads

Add a Cloudflare rate limit for the Worker download path `/d/*`; tokens are
bearer credentials until they expire. The Worker has no built-in per-IP limit.
Download token expiry is clamped to the file's own expiry.

## Route-specific deployment

- [sss3 with Cloudflare and Caddy](../guides/sss3-cloudflare.md)
- [Tailscale-only sss3](../guides/tailscale-sss3.md)
- [B2 private bucket with Cloudflare Worker](../guides/b2-worker.md)

The security properties are summarized in
[Security model](security.md).
