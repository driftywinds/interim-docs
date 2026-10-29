# interim-docs

Documentation site for [interim](https://github.com/driftywinds/interim), a
temporary file host backed by S3-compatible storage.

The site is built with [ProperDocs](https://properdocs.org) — the maintained
continuation of MkDocs — using the MaterialX theme. Source lives in `docs/`;
config lives in `properdocs.yml`. It is deployed with
[Cloudflare Pages](https://developers.cloudflare.com/pages/).

## Requirements

- Python 3.9+
- pip

## Preview locally

```sh
python -m venv .venv
. .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
properdocs serve            # http://127.0.0.1:8000
```

The dev server watches `docs/` and `properdocs.yml` and reloads the browser.

## Build

```sh
properdocs build            # writes ./site
properdocs build --strict   # fail on warnings; used by CI and Cloudflare Pages
python scripts/check_links.py
```

The output in `site/` is static and can be served from any web host.

## Deploy to Cloudflare Pages

### Connect the repository (recommended)

1. In the Cloudflare dashboard, open **Workers & Pages** → **Create** →
   **Pages** → **Connect to Git**.
2. Select this repository and the `main` branch.
3. Use these build settings:

   | Setting | Value |
   | --- | --- |
   | Framework preset | None |
   | Build command | `pip install -r requirements.txt && python -m properdocs build --strict` |
   | Build output directory | `site` |

4. Add an environment variable `PYTHON_VERSION=3.12` for both production and
   preview builds. Cloudflare's default Python is older than some dependencies
   expect.
5. Deploy. Every push to `main` publishes the site; pull requests get a preview
   deployment.

### Deploy from the command line

```sh
pip install -r requirements.txt
properdocs build --strict
npx wrangler pages deploy site --project-name interim-docs
```

`wrangler.toml` already declares `pages_build_output_dir = "site"`.

### Set the real URL

`site_url` in `properdocs.yml` is `https://interim-docs.pages.dev/`. Change it
to the production domain (for example `https://docs.example.com/`) so canonical
links, the sitemap, and the `robots.txt` reference are correct. If the project
name differs, update `robots.txt` and `wrangler.toml` too.

`docs/_headers` is copied into the build output and configures security headers
and cache lifetimes for Cloudflare Pages.

## Layout

```text
properdocs.yml          site config, theme, Markdown extensions, nav
requirements.txt        pinned ProperDocs and theme versions
wrangler.toml           Cloudflare Pages project config
scripts/check_links.py  internal link and anchor checker used by CI
docs/
  index.md              home page
  getting-started/      quick start and storage route selection
  guides/               S3, sss3 + Cloudflare, Tailscale, B2 + Worker
  usage/                web UI, API, admin
  reference/            configuration reference
  operations/           capacity/retention, deployment, security model
  contributing/         development, architecture, contributing, security, license
  assets/               favicon, extra CSS
  _headers, robots.txt  copied into the build output
```

## Keeping content in sync

The upstream repository keeps plain Markdown in `docs/` plus
`CONTRIBUTING.md` and `SECURITY.md`. This site reorganizes that material and
links back to the repository for files such as `compose.sss3.yaml`,
`Caddyfile.sss3`, and the Cloudflare Worker. When upstream behavior changes,
update when upstream behavior changes,
update the matching page here and the version pins in `requirements.txt` only
when the toolchain changes.

## License

GNU Affero General Public License v3.0. See [LICENSE](LICENSE).

Copyright (C) 2026 driftywinds.
