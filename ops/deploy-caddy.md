# Caddy binary rebuild runbook

## Why this exists

Stock Caddy from the Ubuntu 24.04 apt repository does not ship the
`mholt/caddy-ratelimit` third-party module. The T-020 spike on 2026-04-21
rebuilt Caddy v2.11.1 with `mholt/caddy-ratelimit` via xcaddy 0.4.5 so
the per-IP rate-limit behaviour required by the graphwash site block
becomes available. The site fragment at `ops/graphwash.Caddyfile`
depends on the `rate_limit` directive, so any host that serves graphwash
must run this rebuilt binary or the Caddyfile will fail to load.

## Prerequisites

- SSH root access to helsinki-paradise (`157.180.94.145`).
- Go 1.22 or newer, installed from apt: `apt install golang-go`.
- xcaddy 0.4.5, installed via Go:

```bash
go install github.com/caddyserver/xcaddy/cmd/xcaddy@v0.4.5
```

The resulting `xcaddy` binary lands in `$(go env GOPATH)/bin`. Add that
directory to `PATH` for the current shell, or invoke `xcaddy` by its
absolute path.

## Build procedure

Run the exact command captured during the T-020 spike:

```bash
cd /root/xcaddy-build
xcaddy build v2.11.1 \
    --with github.com/mholt/caddy-ratelimit \
    -tags nobadger,nomysql,nopgx
```

The build tags drop unused storage backends (Badger, MySQL, pgx). They
keep the binary smaller and match the storage surface of the stock apt
build, so behaviour stays consistent with what Ubuntu ships.

## Binary swap procedure

Linux locks running executables, so an in-place `cp` over `/usr/bin/caddy`
while caddy is running fails with `Text file busy`. The fix is to stop
caddy, swap the binary, then restart. This causes a roughly three-second
outage on every site this VPS serves (graphwash, claude-api, exhibita),
so schedule the swap during a low-traffic window and announce it if any
collaborator is depending on the box.

```bash
systemctl stop caddy
cp /usr/bin/caddy /usr/bin/caddy.apt-backup    # only on first install
cp /root/xcaddy-build/caddy /usr/bin/caddy
systemctl start caddy
systemctl status caddy
```

The backup copy step runs only on the first install. On later rebuilds,
preserve the existing `/usr/bin/caddy.apt-backup` so the rollback path
still resolves to the original apt binary.

## Verification

Confirm the rate-limit module is registered:

```bash
caddy list-modules | grep rate_limit
```

The output must include `http.handlers.rate_limit`. If the line is
absent, the build did not include the module. Roll back to the apt
binary using the procedure below, then rebuild and re-verify before
swapping again.

## Rollback

Restore the apt binary captured during the first install:

```bash
systemctl stop caddy
cp /usr/bin/caddy.apt-backup /usr/bin/caddy
systemctl start caddy
caddy version
```

`caddy version` should print the apt-shipped version string. The
graphwash site block will fail to load whilst the apt binary is in
place, because `rate_limit` is unknown to it. Treat rollback as a
short-lived recovery state, not a steady configuration.

## Cross-references

The graphwash site fragment lives at `ops/graphwash.Caddyfile` in this
repository. The full live `/etc/caddy/Caddyfile` on helsinki-paradise is
the union of three application blocks (graphwash, claude-api,
exhibita); only the graphwash fragment is version-controlled here. When
editing the fragment, copy it into the live Caddyfile by hand and run
`caddy validate --config /etc/caddy/Caddyfile` before reloading.
