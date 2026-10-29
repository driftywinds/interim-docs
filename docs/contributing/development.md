---
description: Tests, vet, local runs, direct builds, and documentation previews.
---

# Development

Go 1.27 is used in the Docker image. Node.js 22+ is needed only for the
Cloudflare Worker.

```sh
go test ./...
go vet ./...
go build ./...
gofmt -l .
go run ./cmd/interim
```

Match the existing style: `gofmt`, no new dependencies without a reason, and
tests for behavior changes.

## Test coverage

The test suite uses an in-memory fake object store and covers setup token
enforcement, auth, upload-intent creation, staging-to-live copy-on-complete,
single-PUT completion, multipart part URLs/reporting/status/completion/abort,
exact part-size validation, oversized-provider-part rejection, abort-failure
retention, orphan multipart sweeping, endpoint rate limits, multipart janitor
cleanup, idempotent completion, direct upload verification, ownership,
per-client and global quota rejection, abort, janitor expiry, orphan sweeping,
expiry cleanup, admin deletion, restricted-upload enforcement, admin-generated
hashes, approval changes, trusted-proxy parsing, cookie naming, and schema
migrations.

S3 integration, CORS, `CopyObject`, multipart, and presigned PUT behaviour must
be tested against your provider.

## Build the binary directly

```sh
CGO_ENABLED=0 go build -trimpath -o bin/interim ./cmd/interim
```

## Worker

```sh
cd worker
npm ci
node --check src/index.js
```

Deployment for the Worker is covered in
[B2 with a Cloudflare Worker](../guides/b2-worker.md).

## Documentation site

This documentation site is a separate repository that builds with
[ProperDocs](https://properdocs.org). To preview changes:

```sh
pip install -r requirements.txt
py -m properdocs serve
```

Then edit `docs/` and the dev server reloads automatically. Before opening a
pull request, build with warnings treated as errors and check internal links:

```sh
py -m properdocs build --strict
python scripts/check_links.py
```

## Related pages

- [Architecture](architecture.md) — how the packages fit together.
- [Contributing guide](contributing.md) — repository rules.
- [Configuration](../reference/configuration.md) — runtime settings.
