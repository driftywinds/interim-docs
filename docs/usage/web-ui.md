---
description: Browser uploads, local history, resume, and restricted-upload mode.
---

# Web UI and browser history

The home page creates an upload intent, PUTs the selected file directly to S3
with XHR for progress, then calls the completion endpoint. Canceling aborts the
intent. Upload URLs are short-lived, so a slow upload can fail before completion;
the UI reports that and tells the user to try again.

## Multipart uploads in the browser

When multipart uploads are enabled and a file exceeds the configured threshold,
the browser uploads parts concurrently, retries failed parts independently, and
reports each ETag to interim. Failed tasks show a **Retry** button that queries
the server for completed parts and continues; it does not recreate the upload.

Interrupted multipart sessions are stored in `localStorage` under
`interim.multipart.v1` along with the upload token. Select the same file again
to resume from the recorded parts; the interrupted-upload list also offers
**Discard**, which aborts the server-side multipart upload. Session API URLs are
accepted only when they are same-origin with the UI; malformed or cross-origin
session records are discarded.

!!! warning "The upload token is a bearer credential"

    Treat browser storage like the delete token. The multipart resume record
    keeps the upload token in `localStorage`.

## Browser history

Completed uploads are stored in `localStorage` under `interim.uploads.v1`,
including the per-file delete token. Only that browser can see the list.
Clearing site data loses the local delete ability, but the file still expires
after the configured `RETENTION` period (or, when
`RETENTION_EXTEND_ON_DOWNLOAD=true`, after `RETENTION` from the last download)
and the admin can delete it.

## Restricted upload mode

When `PUBLIC_UPLOADS_ENABLED=false`, the home page asks for an admin-issued
user hash. It validates the hash with `GET /api/v1/keys/me`, requires
`approved: true`, and stores it in `localStorage` under
`interim.uploadHash.v1`. Future upload intents send it as a bearer token.
Invalid, revoked, or unapproved hashes clear the saved value and reopen the
prompt. The **Forget** button removes it from the browser.

The hash is never put in a URL or log line. Anyone with access to that browser
profile can read the stored value, so treat it like a password.

## Download pages

The download page never receives or displays the delete token. Its download
button links to a server endpoint that creates a fresh download link and
redirects to it. Direct object URLs do not exist in the HTML.

## Browser storage keys

| Key | Contents | Treat it like |
| --- | --- | --- |
| `interim.uploads.v1` | Completed uploads, including each file's delete token | A delete credential |
| `interim.multipart.v1` | Interrupted multipart sessions, including the upload token | An upload credential |
| `interim.uploadHash.v1` | The approved user hash in restricted mode | A password |

Clearing site data removes all three. The files themselves stay until their
expiry, and the admin can delete them.

## Design

The UI is deliberately minimal: system sans-serif, no webfonts, no logo image,
native controls, automatic light/dark mode, and monospace filenames.

## Related pages

- [Admin](admin.md) — generating and approving user hashes.
- [API](api.md) — the same flow from scripts.
- [Security model](../operations/security.md) — why anonymous credentials live
  in `localStorage`.
