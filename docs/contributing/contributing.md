---
description: Repository rules, style, and pull request expectations for interim.
---

# Contributing guide

Thanks for considering a change. Keep pull requests focused and small.

## Requirements

Go 1.27+, Node.js 22+ (worker only), and optionally Docker.

```sh
go test ./...
go vet ./...
go build ./...
```

Worker:

```sh
cd worker
npm ci
node --check src/index.js
```

## Style

Match the existing style: `gofmt`, no new dependencies without a reason, and
tests for behavior changes. Security-sensitive changes should explain the trust
boundary they touch.

## Rules

- Never commit real credentials, `.env` files, bucket names, private hostnames,
  Cloudflare IDs, or captured browser data. Use the `*.example` files.
- Do not open a public issue for a vulnerability. Follow the
  [security policy](security-policy.md).
- By contributing, you agree that your contribution is licensed under the GNU
  Affero General Public License v3.0 in
  [`LICENSE`](https://github.com/driftywinds/interim/blob/main/LICENSE).

## Pull requests

- Describe the behavior change and how you tested it.
- Call out any new environment variable, endpoint, or migration.
- Keep documentation in sync; user-visible behavior belongs in this site and in
  the interim repository's `docs/` directory.

## Related pages

- [Development](development.md) — commands and test coverage.
- [Architecture](architecture.md) — where to change things.
- [Security policy](security-policy.md) — private vulnerability reporting.
