---
description: Admin capabilities, user hashes, approvals, and session controls.
---

# Admin

`/admin` is gated by a DB-backed session created during first-run setup. Setup
requires the one-time `SETUP_TOKEN` (or `DATA_DIR/setup_token`).

## What the admin can do

- See storage usage, the hard cap, active reservations, and every file.
- Search by filename or ID and paginate.
- Open files, delete one file, or select and bulk-delete (S3 object first).
- Generate an approved user hash for someone and show it once.
- Inspect user-hash prefixes, approval, usage, and last-used time.
- Set a per-hash file-size limit and retention override.
- Approve/unapprove uploads and revoke/restore authentication without exposing
  the raw hash.

## Per-hash limits

Per-hash limits default to the instance `MAX_FILE_SIZE` and `RETENTION`. Set
either to `0` for unlimited: a hash with `max_file_size=0` may exceed the
instance file-size default (up to the provider limit), and a hash with
`retention=0` gets files that never expire. The retention value is captured when
each upload commits, so later edits apply to new files only. Hashes that predate
this feature inherit the instance defaults until edited.

## Example: onboarding someone in restricted mode

1. Open `/admin` → **User hashes** → generate a hash. It is approved
   automatically.
2. Optionally raise or lower `max_file_size` and `retention` for that hash.
   Leaving both empty uses the instance defaults.
3. Copy the hash immediately; it is shown once and never again.
4. Send it over a channel you trust. The recipient pastes it into the prompt on
   the home page, or uses it as `Authorization: Bearer interim_…` in scripts.
5. To stop access, revoke the hash from the same table. New uploads fail
   immediately; files already committed keep their expiry and remain
   downloadable until then.

!!! warning "The hash is a password"

    Anyone with the hash can upload as that user and list or delete their files.
    Store it in a password manager, not in a shared note or a public CI log.

## Sessions and passwords

Admin POSTs are CSRF-protected. Login is rate-limited per IP and per account;
password minimum is 12 characters. Passwords are bcrypt hashes (cost 12).

Sessions have an absolute `ADMIN_SESSION_TTL` and an idle `ADMIN_IDLE_TIMEOUT`.
**Logout** ends the current session; **Sign out everywhere** revokes every
session for the admin. The **Admin password** form changes the password after
verifying the current one and revokes every session, including the current
browser. There is intentionally only one admin account.

## Restricted uploads

When `PUBLIC_UPLOADS_ENABLED=false`, only approved hashes can upload. Hashes
that existed before the switch are not grandfathered in, so approve them from
this page. A generated hash is approved automatically and shown only once.

See [Security model](../operations/security.md) for session and credential
handling.
