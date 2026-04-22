# Hetzner VPS operations reference

Reference for the `graphwash.dineshd.dev` deployment on the shared
`helsinki-paradise` VPS. Covers instance metadata, the Caddy site block,
SSH access, container lifecycle, and the T-019 spike measurement evidence.

## Instance

| Field                  | Value                                                                  |
| ---------------------- | ---------------------------------------------------------------------- |
| Public hostname        | graphwash.dineshd.dev                                                  |
| Public IPv4            | 157.180.94.145                                                         |
| Public IPv6            | 2a01:4f9:c013:d2de::1                                                  |
| Instance id            | 117529019                                                              |
| Provisioning hostname  | ubuntu-4gb-hel1-1                                                      |
| Location               | Hetzner Cloud, hel1-dc2 (Helsinki, datacentre 2)                       |
| Region code            | eu-central                                                             |
| OS                     | Ubuntu 24.04.4 LTS                                                     |
| Kernel                 | 6.8.0-110-generic                                                      |
| CPU                    | 4 vCPU AMD EPYC-Genoa shared                                           |
| RAM                    | 7.6 GiB                                                                |
| Disk                   | 75 GB (ext4 on `/dev/sda1`)                                            |
| Swap                   | 4 GiB (`/swapfile`, added 2026-04-21 for T-019)                        |
| SSH host key (ed25519) | `AAAAC3NzaC1lZDI1NTE5AAAAIAej0hhEjgVI2n7QhIRGQZCM4R9FMhojD/j3qF3WoGwn` |

The host is shared with `claude-api.service`
(`api.claudehome.dineshd.dev`, localhost:8000) and `exhibita`
(`exhibita.dineshd.dev`, localhost:8001). graphwash binds
`127.0.0.1:8002`.

## Caddy site block

The live `/etc/caddy/Caddyfile` on the VPS is the union of three site
blocks (graphwash, claude-api, exhibita). Only the graphwash fragment is
version-controlled in this repo, at
[`../../ops/graphwash.Caddyfile`](../../ops/graphwash.Caddyfile). Treat
that file as the source of truth for the graphwash block; the
co-tenant blocks live only on the host.

Caddy manages TLS automatically via ACME (Let's Encrypt). The access log
file must be owned by `caddy:caddy` before reload; a reload that creates
the file under `root:root` will fail the permission check and leave the
daemon in a stuck reloading state.

## T-019 measurements (PRD §11a S-03)

All four acceptance gates recorded 2026-04-21 against
`graphwash:t-019-spike` on `helsinki-paradise`.

### Cold-start (target: < 30 s)

Command: `/tmp/t019-cold-start.sh`, 5 iterations of `docker rm -f` +
`docker run -d` + poll `/api/v1/health` until 200.

```text
iter 1: 2.494s
iter 2: 2.436s
iter 3: 2.405s
iter 4: 2.460s
iter 5: 2.486s
```

Range: 2.405 to 2.494 s. All five iterations cleared the 30 s target.

### Idle RAM (target: < 2 GB container RSS)

Command: `docker stats --no-stream graphwash`, three readings at 30 s
intervals.

```text
iter 1: mem=74.56MiB / 7.564GiB cpu=0.19% pid_count=12
iter 2: mem=74.57MiB / 7.564GiB cpu=0.22% pid_count=12
iter 3: mem=74.57MiB / 7.564GiB cpu=0.19% pid_count=12
```

Steady-state RSS: 74.56 to 74.57 MiB. Cleared the 2 GiB target with
substantial headroom.

The `HGTStub` (`src/graphwash/api/hgt_stub.py`) loads no model weights,
so this reading does not generalise to the real HGT model in Phase 2.
The binding RAM verdict defers to the Phase 2 gate per ADR-0006.

### `/api/v1/health` p95 latency (target: < 50 ms)

Command: `ab -n 500 -c 10 https://graphwash.dineshd.dev/api/v1/health`.

The plan specified `hey` for load generation. Its S3 distribution URL
returned 403 at measurement time. Apache `ab` from `apache2-utils` was
used as the equivalent percentile-reporting substitute.

Public HTTPS (via Caddy + TLS):

```text
Concurrency Level:      10
Time taken for tests:   2.339 seconds
Complete requests:      500
Failed requests:        0
Requests per second:    213.78 [#/sec] (mean)
Time per request:       46.777 [ms] (mean)

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        1    3   1.4      2      13
Processing:    41   43   1.2     43      49
Waiting:       41   43   1.1     43      48
Total:         42   46   2.1     45      60

Percentage of the requests served within a certain time (ms)
  50%     45
  66%     46
  75%     46
  80%     46
  90%     47
  95%     49
  98%     53
  99%     55
 100%     60 (longest request)
```

Localhost baseline (direct to uvicorn on port 8002, no TLS):

```text
Concurrency Level:      10
Time taken for tests:   0.261 seconds
Complete requests:      500
Failed requests:        0
Requests per second:    1914.09 [#/sec] (mean)
Time per request:       5.224 [ms] (mean)

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.1      0       1
Processing:     1    5   1.5      5      16
Waiting:        1    5   1.5      5      15
Total:          2    5   1.6      5      16

Percentage of the requests served within a certain time (ms)
  50%      5
  66%      5
  75%      5
  80%      6
  90%      6
  95%      7
  98%     11
  99%     15
 100%     16 (longest request)
```

Public p95: 49 ms. Localhost p95: 7 ms. The ~42 ms delta is TLS
handshake plus network round-trip. `ab` without keepalive establishes a
fresh TLS handshake per request; keepalive'd production traffic would be
materially tighter. The 49 ms result cleared the < 50 ms target.

### Caddy TLS issuance (target: < 2 min)

Measurement window: `tls.obtain "obtaining certificate"` through
`tls.obtain "certificate obtained successfully"` in
`journalctl -u caddy`.

```text
{"level":"info","ts":1776806697.9267936,"logger":"tls.obtain","msg":"obtaining certificate","identifier":"graphwash.dineshd.dev"}
{"level":"info","ts":1776806698.9692035,"msg":"trying to solve challenge","identifier":"graphwash.dineshd.dev","challenge_type":"http-01","ca":"https://acme-v02.api.letsencrypt.org/directory"}
{"level":"info","ts":1776806699.2915447,"logger":"http","msg":"served key authentication","identifier":"graphwash.dineshd.dev","challenge":"http-01","remote":"[2600:3000:1305:4212::82]:45681","distributed":false}
{"level":"info","ts":1776806699.5854871,"logger":"http","msg":"served key authentication","identifier":"graphwash.dineshd.dev","challenge":"http-01","remote":"[2a05:d016:39f:3101:d441:6a08:d97a:4010]:12976","distributed":false}
{"level":"info","ts":1776806699.6112685,"logger":"http","msg":"served key authentication","identifier":"graphwash.dineshd.dev","challenge":"http-01","remote":"[2600:1f16:269:da02:4091:e3c9:4701:41da]:21740","distributed":false}
{"level":"info","ts":1776806699.6771846,"logger":"http","msg":"served key authentication","identifier":"graphwash.dineshd.dev","challenge":"http-01","remote":"[2600:1f14:804:fd02:28ea:521:b3dc:d322]:40010","distributed":false}
{"level":"info","ts":1776806699.834555,"logger":"http","msg":"served key authentication","identifier":"graphwash.dineshd.dev","challenge":"http-01","remote":"[2406:da18:85:1400:8843:d5a9:c731:7f7c]:55658","distributed":false}
{"level":"info","ts":1776806702.5841188,"logger":"tls.obtain","msg":"certificate obtained successfully","identifier":"graphwash.dineshd.dev","issuer":"acme-v02.api.letsencrypt.org-directory"}
{"level":"info","ts":1776806702.5842557,"logger":"tls.obtain","msg":"releasing lock","identifier":"graphwash.dineshd.dev"}
```

Elapsed: 4.66 s (`1776806702.584` − `1776806697.927`). Cleared the
< 2 min target. Certificate: Let's Encrypt E7, CN=`graphwash.dineshd.dev`,
valid 2026-04-21 → 2026-07-20.

## SSH access

```bash
ssh root@157.180.94.145
```

The hostname resolves to the same IP:

```bash
ssh root@graphwash.dineshd.dev
```

Authentication is pubkey only. The authorised key is the same ed25519
key used across `helsinki-paradise`. Password authentication is
disabled.

To verify the host before first connection:

```text
Host key (ed25519): AAAAC3NzaC1lZDI1NTE5AAAAIAej0hhEjgVI2n7QhIRGQZCM4R9FMhojD/j3qF3WoGwn
```

## Container lifecycle

**Inspect running container:**

```bash
docker inspect graphwash
docker logs graphwash
docker logs --tail 50 -f graphwash
```

**Check health:**

```bash
curl -s http://127.0.0.1:8002/api/v1/health
```

**Restart without redeploying:**

```bash
docker restart graphwash
```

**Redeploy (rebuild from local `HEAD` and replace container):**

No container registry is used. Images are built on the VPS from a
`git archive HEAD` stream, from a checkout of the graphwash repo on
the local machine:

```bash
git archive HEAD | ssh root@157.180.94.145 \
    'docker build -t graphwash:TAG -'

ssh root@157.180.94.145 bash <<'EOF'
docker rm -f graphwash
docker run -d \
    --name graphwash \
    --restart unless-stopped \
    -p 127.0.0.1:8002:8002 \
    graphwash:TAG
EOF
```

**Check Caddy:**

```bash
systemctl status caddy
journalctl -u caddy -n 50
caddy validate --config /etc/caddy/Caddyfile
```

**Reload Caddy after a Caddyfile edit:**

```bash
systemctl reload caddy
```

## Rollback

T-019 is the spike; no production traffic depends on it. Rollback is:

```bash
docker rm -f graphwash
```

Caddy returns 502 for `graphwash.dineshd.dev` but continues serving
`api.claudehome.dineshd.dev` and `exhibita.dineshd.dev` uninterrupted.

## Caddy binary upgrade

The stock apt-installed Caddy on Ubuntu 24.04 ships without the
`mholt/caddy-ratelimit` module. The per-IP rate-limit added on
2026-04-21 (T-020 spike) requires that module, so the binary was
rebuilt via `xcaddy`.

- Version installed: Caddy v2.11.1 with `mholt/caddy-ratelimit`, built
  with `xcaddy 0.4.5`.
- Build tags: `-tags nobadger,nomysql,nopgx` to drop unused storage
  backends and match the stock apt build size.
- Original apt binary preserved at `/usr/bin/caddy.apt-backup` (47.4
  MB) as the rollback target.
- Linux locks running executables, so an in-place `cp` over
  `/usr/bin/caddy` while caddy is running fails with `Text file busy`.
  Always `systemctl stop caddy` before swapping the binary. The brief
  outage (around 3 seconds) affects all three sites on this VPS;
  accept that or schedule the swap.
- Full runbook: [`../../ops/deploy-caddy.md`](../../ops/deploy-caddy.md).
