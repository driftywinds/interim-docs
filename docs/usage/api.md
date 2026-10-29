---
description: Upload, download, and manage files with the interim REST API.
---

# API

Start at `/api` for the rendered documentation or `/api/openapi.json` for the
OpenAPI 3.1 document. Examples use `PUBLIC_BASE_URL`.

## Authentication

By default, upload intents are public. Set `PUBLIC_UPLOADS_ENABLED=false` to
require an admin-approved user hash. In that mode `POST /api/v1/keys` is
disabled, and every existing or self-created hash stays unapproved until an
admin approves it in `/admin`.

| Mode | Create intent | Error |
| --- | --- | --- |
| Public uploads | No credential, or any valid hash | — |
| Restricted, anonymous | No credential | `401 uploads_restricted` |
| Restricted, unapproved hash | Valid but unapproved hash | `403 upload_not_allowed` |

Completion and abort still use only the upload token.

Three credentials exist, and they are not interchangeable:

- **User hash** (`interim_…`): bearer token for API calls, upload attribution,
  and listing or deleting the caller's files. Stored only as a SHA-256 hash.
- **Upload token**: returned once per upload intent, sent in `X-Upload-Token`
  for completion, abort, and multipart calls. Stored only as a SHA-256 hash.
- **Delete token**: returned once when the upload intent is created, sent in
  `X-Delete-Token` to delete an anonymous file. Stored only as a SHA-256 hash.

## Upload flow

=== "Shell"

    ```sh
    # Create a user hash (shown once; public mode only)
    curl -X POST https://files.example.com/api/v1/keys \
      -H 'Content-Type: application/json' \
      -d '{"name":"cli"}'

    # Create an upload intent
    curl -X POST https://files.example.com/api/v1/uploads \
      -H 'Authorization: Bearer interim_...' \
      -H 'Content-Type: application/json' \
      -d '{"name":"sample.bin","size":12345,"content_type":"application/octet-stream"}'

    # PUT the file bytes directly to the signed URL from that response
    curl -X PUT 'SIGNED_S3_URL' \
      -H 'Content-Type: application/octet-stream' \
      -H 'Content-Disposition: attachment; filename=sample.bin' \
      --data-binary @sample.bin

    # Verify and commit it
    curl -X POST 'COMPLETE_URL' \
      -H 'X-Upload-Token: UPLOAD_TOKEN'

    # Get a download URL (expires after DOWNLOAD_URL_TTL)
    curl -X POST https://files.example.com/api/v1/files/FILE_ID/download

    # Delete with the owning user hash
    curl -X DELETE https://files.example.com/api/v1/files/FILE_ID \
      -H 'Authorization: Bearer interim_...'
    ```

=== "Python"

    ```python
    import json
    import urllib.request

    BASE = "https://files.example.com"
    HASH = "interim_..."  # omit for anonymous uploads in public mode


    def post(path, payload, token=None, extra_headers=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        headers.update(extra_headers or {})
        request = urllib.request.Request(
            BASE + path,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            return json.load(response)


    with open("sample.bin", "rb") as handle:
        data = handle.read()

    intent = post(
        "/api/v1/uploads",
        {
            "name": "sample.bin",
            "size": len(data),
            "content_type": "application/octet-stream",
        },
        token=HASH,
    )

    # The signed headers are part of the signature and must be sent unchanged.
    put = urllib.request.Request(
        intent["url"], data=data, headers=intent["headers"], method="PUT"
    )
    with urllib.request.urlopen(put) as response:
        response.read()

    # Commit the upload. Completion is idempotent, so a retry is safe.
    complete = urllib.request.Request(
        intent["complete_url"],
        data=b"",
        headers={"X-Upload-Token": intent["upload_token"]},
        method="POST",
    )
    with urllib.request.urlopen(complete) as response:
        file = json.load(response)["file"]

    print("page:", file["page_url"])
    print("delete token:", intent["delete_token"])
    ```

The single-PUT URL signs the intent's declared `Content-Length`, and completion
requires the stored object to have exactly that size.

## Response shapes

A single-PUT intent (values trimmed):

```json
{
  "upload_id": "up_01J8Z0…",
  "mode": "single",
  "url": "https://s3.example.com/interim/files/uploads/up_01J8Z0…?X-Amz-Signature=…",
  "method": "PUT",
  "headers": {
    "Content-Type": "application/octet-stream",
    "Content-Disposition": "attachment; filename=\"sample.bin\""
  },
  "expires_at": "2026-01-01T12:30:00Z",
  "intent_expires_at": "2026-01-01T12:45:00Z",
  "upload_token": "…",
  "complete_url": "https://files.example.com/api/v1/uploads/up_01J8Z0…/complete",
  "abort_url": "https://files.example.com/api/v1/uploads/up_01J8Z0…",
  "delete_token": "…",
  "delete_token_header": "X-Delete-Token",
  "warning": "Upload directly to the signed URL, then call complete_url with the upload token. Keep delete_token private."
}
```

A multipart intent adds part metadata and omits `url`:

```json
{
  "upload_id": "up_01J8Z1…",
  "mode": "multipart",
  "part_size": 16777216,
  "part_count": 4,
  "concurrency": 3,
  "parts_url": "https://files.example.com/api/v1/uploads/up_01J8Z1…/parts",
  "status_url": "https://files.example.com/api/v1/uploads/up_01J8Z1…",
  "intent_expires_at": "2026-01-01T12:45:00Z",
  "upload_token": "…",
  "complete_url": "https://files.example.com/api/v1/uploads/up_01J8Z1…/complete",
  "abort_url": "https://files.example.com/api/v1/uploads/up_01J8Z1…",
  "delete_token": "…"
}
```

Completion returns the committed file:

```json
{
  "upload_id": "up_01J8Z0…",
  "file": {
    "id": "Xy3k…",
    "name": "sample.bin",
    "size": 12345,
    "content_type": "application/octet-stream",
    "created_at": "2026-01-01T12:01:00Z",
    "expires_at": "2026-01-08T12:01:00Z",
    "expires_in_seconds": 604740,
    "never_expires": false,
    "page_url": "https://files.example.com/f/Xy3k…",
    "api_url": "https://files.example.com/api/v1/files/Xy3k…",
    "owner": "user_hash"
  }
}
```

`GET /api/v1/status`:

```json
{
  "accepting_uploads": true,
  "public_uploads": false,
  "storage": {
    "files": 412,
    "used_bytes": 8589934592,
    "reserved_bytes": 104857600,
    "limit_bytes": 21474836480,
    "available_bytes": 12780052480,
    "used_percent": 40,
    "unlimited": false
  },
  "retention_seconds": 604800,
  "retention_human": "7 days",
  "retention_extend_on_download": false,
  "max_file_size_bytes": 5368709120,
  "download_url_ttl_seconds": 300,
  "server_time": "2026-01-01T12:00:00Z"
}
```

## Multipart mode

If `MULTIPART_UPLOAD_ENABLED=true` and the file exceeds `MULTIPART_THRESHOLD`,
the create response has `mode: "multipart"` and no single `url`. It includes
`part_size`, `part_count`, `parts_url`, and `status_url`.

1. `POST parts_url` with `X-Upload-Token` and
   `{"part_numbers":[1,2,3]}`. The response contains short-lived part URLs.
2. PUT each part body to its URL. Read the response `ETag`.
3. `PUT parts_url/{n}` with `{"etag":"...","size":123}` and
   `X-Upload-Token`. `size` must be exact: non-final parts equal `part_size`,
   and the final part equals the remaining bytes. When
   `MULTIPART_SIGN_PART_LENGTH=true`, the part URL signs that Content-Length, so
   send a fixed-length body, not chunked transfer encoding.
4. Repeat until `GET status_url` reports all parts in `completed_parts`.
5. Call `complete_url` with `X-Upload-Token`.

Reporting a part:

```sh
curl -X PUT 'https://files.example.com/api/v1/uploads/up_…/parts/1' \
  -H 'X-Upload-Token: UPLOAD_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"etag":"\"9b2cf535f27731c974343645a3985328\"","size":16777216}'
```

All parts from 1 through `part_count` must be reported before completion; parts
can be uploaded and reported concurrently. The server verifies provider-side
part sizes/ETags, assembles the multipart object, and uses the staging key as the
live object (no second copy). The final `HeadObject` size check still runs. A
provider-side size or ETag mismatch returns `413 part_size_mismatch`. A failed
part can be retried independently; `GET status_url` lets a client resume after
reload.

## Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/keys` | no | Create user hash. Disabled when public uploads are off. |
| `GET` | `/api/v1/keys/me` | bearer | Key prefix, approval, usage, and per-hash limits. |
| `POST` | `/api/v1/uploads` | optional; approved when restricted | Reserve quota and create single-PUT or multipart upload state. |
| `GET` | `/api/v1/uploads/{id}` | upload token | Multipart status and completed part numbers. |
| `POST` | `/api/v1/uploads/{id}/parts` | upload token | Request up to 100 presigned part URLs. |
| `PUT` | `/api/v1/uploads/{id}/parts/{n}` | upload token | Record a part ETag and size. |
| `POST` | `/api/v1/uploads/{id}/complete` | upload token | Assemble/verify and commit the object. |
| `DELETE` | `/api/v1/uploads/{id}` | upload token | Abort a pending upload and release quota. |
| `GET` | `/api/v1/files` | bearer | List the caller's active files. |
| `GET` | `/api/v1/files/{id}` | no | Public metadata. |
| `POST` | `/api/v1/files/{id}/download` | no | Short-lived download URL. |
| `DELETE` | `/api/v1/files/{id}` | bearer or token | Delete. |
| `GET` | `/api/v1/status` | no | Capacity and retention status. |

## Errors and rate limits

Rate limits apply to user-hash creation, upload-intent creation, download-link
creation, and admin login. Errors use a stable envelope:

```json
{
  "error": {
    "code": "upload_not_allowed",
    "message": "This user hash is valid but is not approved for uploads.",
    "request_id": "8f14e45fceea167a"
  }
}
```

Include the `request_id` when reporting a problem. `429` responses carry a
`Retry-After` header in seconds.

## Related pages

- [Admin](admin.md) — the upload allowlist and admin-side key generation.
- [Capacity and retention](../operations/capacity-and-retention.md) — quota and
  expiry behavior.
- [Web UI](web-ui.md) — the same flow in the browser.
