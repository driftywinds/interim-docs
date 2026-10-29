---
description: Compare direct S3, sss3 behind Cloudflare, Tailscale-only sss3, and B2 with a Worker.
---

# Choosing a storage route

interim works with any S3-compatible endpoint, but the route you pick decides how
large uploads can get, where the bytes flow, and what you have to operate.

## Side by side

| Route | Browser talks to | Cloudflare in the data path | Practical upload limit |
| --- | --- | --- | --- |
| [Direct S3-compatible storage](../guides/s3-compatible-storage.md) | The provider endpoint | No | Provider object limit (5 GB single PUT, multipart above) |
| [sss3 with Cloudflare and Caddy](../guides/sss3-cloudflare.md) | Caddy in front of sss3, via a Cloudflare Tunnel | Yes, proxied | About 100 MB per request on Free/Pro |
| [Tailscale-only sss3](../guides/tailscale-sss3.md) | A small VPS that forwards over the tailnet | No, for the S3 hostname | Provider object limit, no Cloudflare cap |
| [B2 with a Cloudflare Worker](../guides/b2-worker.md) | B2 for uploads, the Worker for downloads | Only for downloads | Provider object limit |

## Pick by what you have

- **AWS, MinIO, R2, Wasabi, or B2 with a public endpoint:** start with
  [S3-compatible storage](../guides/s3-compatible-storage.md). Nothing extra to
  run; the bucket needs CORS.
- **A home server behind CGNAT running sss3:** use the
  [Tailscale-only route](../guides/tailscale-sss3.md) if you need files larger
  than Cloudflare's request-body cap, or the
  [Cloudflare + Caddy route](../guides/sss3-cloudflare.md) if small files are
  enough.
- **Free egress without a public bucket:** use B2 with the
  [Cloudflare Worker download proxy](../guides/b2-worker.md). Uploads still go
  straight to B2.

## What every route needs

- **A private bucket.** Only presigned uploads and short-lived download URLs are
  exposed. Do not enable public ACLs or bucket policies.
- **A browser-reachable `S3_PUBLIC_ENDPOINT`.** It is embedded in presigned URLs.
  For sss3 and Tailscale routes it differs from the server-side `S3_ENDPOINT`.
- **CORS on the bucket** for `PUT` from the interim origin, with the headers
  listed in the create-upload response, and `ETag` exposed for multipart.
  sss3 has no CORS support, so a proxy must answer `OPTIONS`.
- **HTTPS on both origins** when `PUBLIC_BASE_URL` is HTTPS, or the browser
  blocks the upload as mixed content.

!!! tip "Check the route before you commit to it"

    Upload a file larger than the limit you care about through the real browser,
    not curl. Cloudflare's body cap, browser integrity checks, and proxy header
    stripping only show up in a real browser upload.

## Related pages

- [Configuration](../reference/configuration.md) — `S3_*`, upload, and retention
  settings.
- [Deployment notes](../operations/deployment.md) — TLS, proxies, and SQLite
  constraints.
- [Security model](../operations/security.md) — trust boundaries for each route.
