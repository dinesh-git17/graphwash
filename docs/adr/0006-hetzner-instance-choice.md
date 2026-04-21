# ADR 0006: Reuse existing hel1-dc2 8 GB VPS for graphwash deployment

**Status:** Accepted (2026-04-21)

## Context

PRD §11a spike S-03 targeted a dedicated Hetzner CPX31 (or closest
equivalent at 16 GB RAM or greater) for the graphwash container. The
16 GB floor was pinned across REQ-021, §8 P0 NFR, §9 NFR performance,
§11 assumption 5, §12 dependency table, and §13 break-question row 5.

An existing Hetzner hel1-dc2 instance is already live as the
`helsinki-paradise` host for the `claudehome` subdomain family. It is a
4 vCPU AMD EPYC-Genoa box with 7.6 GiB RAM and 75 GB disk, currently
hosting `claude-api.service` (61 MB RSS) and `exhibita` (50 MB RSS),
with 6.9 GiB free at rest.

Options considered:

1. **Provision a new CPX31 (or similar, 16 GB)** per the original PRD
   target. Clean single-tenant deploy.
2. **Reuse the existing hel1-dc2 8 GB instance** as a co-tenant alongside
   `claude-api.service` and `exhibita`. Add swap for OOM insurance.
3. **Provision a new smaller CAX11 (4 GB)** as a graphwash-dedicated
   host, dropping RAM floor to 4 GB.

## Decision

Option 2. Reuse the existing hel1-dc2 VPS as a co-tenant. Amend the PRD
RAM floor to "8 GB or greater if Phase 2 HGT idle RSS is 3 GB or less,
else 16 GB or greater". The 16 GB tier is kept on the §11a fallback
ladder, triggered by the Phase 2 real-model RAM reading rather than the
T-019 stub measurement.

Added a 4 GiB swapfile before Docker install as OOM insurance for the
co-tenancy. Container binds `127.0.0.1:8002`.

## Consequences

Positive:

- Zero incremental infra cost versus 14 euro per month for a fresh CPX31.
- Retires provisioning, DNS, and Caddy-on-Hetzner as unknowns for free.
  All three are already battle-tested for two live sibling sites.
- T-019's four acceptance measurements focus on what was actually
  unknown: container cold-start, container RSS, health p95, and TLS
  issuance. The host setup itself no longer needs validation.

Negative:

- Shared fate with Claudie. A graphwash container OOM would kernel-kill
  neighbouring services on the same host. Mitigated by the 4 GiB
  swapfile added pre-Docker and by T-020's per-IP rate limit.
- The T-019 stub measures a dummy `HGTStub` class, not the real Phase 2
  HGT. 74 MiB idle RSS passes the 2 GB target against the stub; that
  does not prove 8 GB is sufficient for the real model. This ADR accepts
  that risk and defers the binding verdict to the Phase 2 gate.
- REQ-021, §8 P0 NFR, §9 NFR performance, §11 assumption 5, §12
  dependency table, and §13 break-question row 5 all require
  simultaneous amendment to keep the PRD internally consistent. See the
  PRD change-log entry dated 2026-04-21.

Neutral:

- Introduces Docker as a new deploy pattern on this host. All other
  tenants run bare-metal systemd. Docker CE 29.4.1 was installed on
  2026-04-21 as part of T-019.
- The image is built on the VPS from a `git archive HEAD` stream. No
  container registry is introduced for the spike.
