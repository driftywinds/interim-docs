---
title: Temporary file hosting
description: Temporary file hosting on S3-compatible storage.
hide:
  - navigation
  - toc
---

# interim

**Temporary file hosting on S3-compatible storage.** Uploads are public by
default and can be locked down to admin-approved user hashes. Every file expires
after the configured retention period, and downloads are served through
short-lived URLs from a private bucket.

[Quick start](getting-started/quick-start.md){ .md-button .md-button--primary }
[Configuration](reference/configuration.md){ .md-button }
[API](usage/api.md){ .md-button }

Built in Go with SQLite metadata, a server-rendered web UI, a full REST API, and
Docker as the primary deployment target.

<div class="grid cards" markdown>

-   :material-rocket-launch-outline:{ .lg .middle } **Quick start**

    ---

    Run interim with Docker, create the first admin, and choose a storage route.

    [:octicons-arrow-right-24: Get running](getting-started/quick-start.md)

-   :material-cog-outline:{ .lg .middle } **Configuration**

    ---

    Every environment variable, with defaults, ranges, and validation rules.

    [:octicons-arrow-right-24: Read the reference](reference/configuration.md)

-   :material-cloud-outline:{ .lg .middle } **Storage routes**

    ---

    Direct S3, sss3 behind Cloudflare, Tailscale-only sss3, or B2 with a Worker.

    [:octicons-arrow-right-24: Compare routes](getting-started/storage-routes.md)

-   :material-shield-lock-outline:{ .lg .middle } **Security model**

    ---

    Credentials at rest, upload scoping, private downloads, and admin sessions.

    [:octicons-arrow-right-24: Review the model](operations/security.md)

</div>

## How it works

interim never proxies file bytes. It reserves capacity, signs a short-lived
upload URL, verifies the object, and hands out short-lived download URLs. File
bytes travel directly between the browser and the storage provider.

```text
browser --POST /api/v1/uploads--> interim   reserve quota, sign staging PUT
browser --PUT signed URL-------> S3         bytes land in a staging key
browser --POST complete--------> interim    HeadObject, copy, commit the row
browser --GET /f/{id}/download-> interim    short-lived signed GET or worker URL
browser --GET signed URL-------> S3         bytes leave the provider
```

Everything else — retention, quotas, janitor sweeps, admin actions — operates on
rows in SQLite.

## Features

- Anonymous uploads, or an admin-approved upload allowlist.
- User hashes (`interim_…`) for API access, upload approval, and revocation.
- Direct browser-to-S3 uploads through short-lived presigned PUT URLs.
- Optional S3 multipart uploads with configurable part size and resumable
  browser sessions for large files.
- Private bucket downloads with expiring signed or Worker-proxied URLs.
- Configurable retention, optionally extended on every download, plus per-file
  limits, per-hash overrides, and total storage caps.
- First-run admin setup, file management, and a background janitor.

!!! warning "Public uploads are enabled by default"

    If you do not want anonymous uploads, set `PUBLIC_UPLOADS_ENABLED=false`
    before exposing the instance, and review the abuse and content-handling notes
    in [Security model](operations/security.md).

## Project links

- [Repository](https://github.com/driftywinds/interim) — source, issues, releases
- [Cloudflare Worker setup](guides/b2-worker.md) — private B2 downloads
- [Security policy](contributing/security-policy.md) — private vulnerability reporting
- [License](contributing/license.md) — GNU AGPL v3.0
