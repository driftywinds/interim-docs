---
description: Private B2 downloads through a Cloudflare Worker that streams the bytes.
---

# B2 private bucket with Cloudflare Worker downloads

For Backblaze B2, downloads can be proxied by a Cloudflare Worker so B2 →
Cloudflare traffic is covered by the Bandwidth Alliance while the bucket stays
private. The Worker must stream the bytes; a Worker that only signs a B2 URL and
redirects does not get the free-egress treatment.

```text
browser -> interim /files/{id}/download
        -> 303 https://dl1.example.com/d/<token>
        -> Cloudflare Worker
        -> private B2 object
        -> browser
```

Uploads still go directly to B2 with presigned PUTs, so the Cloudflare 100 MB
request-body limit does not apply to uploads.

## Configure interim

```dotenv
DOWNLOAD_WORKER_ENABLED=true
DOWNLOAD_WORKER_URLS=https://dl1.example.com,https://dl2.example.com
DOWNLOAD_WORKER_SECRET=replace-with-openssl-rand-base64-48

S3_ENDPOINT=https://s3.us-west-004.backblazeb2.com
S3_PUBLIC_ENDPOINT=https://s3.us-west-004.backblazeb2.com
S3_REGION=us-west-004
S3_BUCKET=interim
S3_FORCE_PATH_STYLE=true
S3_AUTO_CREATE_BUCKET=false
```

## Behaviour

- `DOWNLOAD_WORKER_ENABLED=false` keeps the existing presigned S3 GET behavior.
- `DOWNLOAD_WORKER_URLS` is rotated for new download links. All workers must
  share the same `DOWNLOAD_WORKER_SECRET` and read the same private B2 bucket.
- The token includes the object key, filename, and expiry. The Worker verifies
  it, signs a path-style B2 request, and streams the response.
- The Worker sets `Cache-Control: private, no-store`; do not cache tokenized
  downloads.
- `S3_PUBLIC_ENDPOINT` remains the B2 endpoint for uploads, not the Worker.
- The Worker sets `Content-Disposition`, supports `HEAD`, and forwards `Range`
  so large downloads can resume.
- `B2_KEY_PREFIX` is required and must end with `/`; the Worker fails closed
  outside that prefix.
- Worker URLs must use HTTPS. `DOWNLOAD_WORKER_URLS` rejects plain HTTP.
- A token can be replayed until it expires, and every range/HEAD request counts
  against the Worker quota. Add a Cloudflare rate-limiting rule for `/d/*`
  (for example 60 requests/minute per IP), keep `DOWNLOAD_URL_TTL` short, and
  monitor request volume. interim clamps a token's expiry to the file's own
  `expires_at`, so a link cannot outlive retention by a full TTL.
- The Worker rejects token keys containing `..`, empty segments, backslashes, or
  control characters before signing a B2 request. Keep `B2_KEY_PREFIX` scoped to
  the bucket prefix as defence in depth.

## Deploy the Worker

### 1. Backblaze setup

1. Create a **private** B2 bucket.
2. Create a read-only application key with bucket access limited to the interim
   bucket, prefix `files/`, and capabilities `readFiles` (optionally
   `listFiles` for operational checks).
3. Note the endpoint and region, for example
   `https://s3.us-west-004.backblazeb2.com` and `us-west-004`.
4. Configure B2 bucket CORS for the interim origin, the `PUT` method, and the
   `Content-Type` and `Content-Disposition` headers.

### 2. Worker configuration

```sh
cd worker
npm ci
cp example.wrangler.toml wrangler.toml
```

Edit `wrangler.toml` with real domains and B2 details:

```toml
name = "interim-download"
routes = [
  { pattern = "dl1.example.com", custom_domain = true }
]

[vars]
B2_ENDPOINT = "https://s3.us-west-004.backblazeb2.com"
B2_REGION = "us-west-004"
B2_BUCKET = "interim"
B2_ACCESS_KEY_ID = "read-only-key-id"
B2_KEY_PREFIX = "files/"
CORS_ORIGIN = "https://interim.example.com"
```

Set the secrets and deploy:

```sh
npx wrangler secret put B2_SECRET_ACCESS_KEY
npx wrangler secret put DOWNLOAD_TOKEN_SECRET
npx wrangler deploy
```

`DOWNLOAD_TOKEN_SECRET` must exactly match interim's `DOWNLOAD_WORKER_SECRET`
and must be at least 32 characters. The custom domain must be proxied through
Cloudflare; the Worker gets a public TLS certificate automatically.

### 3. Verify

```sh
# interim issues a 303 to the Worker
curl -sI "https://files.example.com/f/FILE_ID/download" | grep -i location

# the Worker answers HEAD for a valid token
curl -sI "https://dl1.example.com/d/<token>"
```

### 4. Multiple worker URLs

`DOWNLOAD_WORKER_URLS` accepts a comma- or whitespace-separated list and rotates
new links across it. To deploy a second Worker in another Cloudflare account:

```sh
cp wrangler.toml wrangler.dl2.toml   # change name and route
CLOUDFLARE_ACCOUNT_ID=<account-id> npx wrangler deploy --config wrangler.dl2.toml
```

The custom domain must belong to a zone in the same account as the Worker;
otherwise use `workers_dev = true` and the `*.workers.dev` URL.

## Quota and cost

Every download, `HEAD`, or range request is one Worker invocation. Large files
do not cost more requests, but download managers that issue many ranges do.

| Plan | Included | Overage |
| --- | ---: | ---: |
| Workers Free | 100,000 requests/day | Hard stop |
| Workers Paid | 10,000,000 requests/month | $0.30 per extra million |

B2 → Cloudflare and Cloudflare → user carry no egress charge under the Bandwidth
Alliance. B2 storage and API calls are billed separately.

!!! warning "Quota and terms of service"

    Cloudflare's free Worker allowance is per account, not per Worker. Multiple
    Worker URLs are useful for separate deployments or redundancy, but using
    extra accounts to evade the free allowance is a terms-of-service risk.
    Cloudflare's large-file/video delivery policy still applies to the download
    domain.

## Token lifetime

The Worker is stateless and cannot revoke an issued token early; expiry is the
revocation mechanism. Treat `/d/*` as public and rate-limit it at Cloudflare.
Deleting the file removes the object, but a token already issued remains valid
(and returns 404) until it expires.

## Related pages

- [S3-compatible storage](s3-compatible-storage.md) — B2 endpoint, region, and
  CORS settings.
- [Configuration](../reference/configuration.md) — `DOWNLOAD_WORKER_*` and
  `DOWNLOAD_URL_TTL`.
- [Deployment notes](../operations/deployment.md) — Cloudflare rate limiting and
  proxy expectations.
