# Security Policy

## Scope

`graphwash` is a portfolio machine-learning demo. It runs on IBM's IT-AML
synthetic dataset, stores no real personal information, and exposes an
unauthenticated public endpoint for evaluation only. It makes no claim of
production readiness and is not a real-money anti-money-laundering system.

## Supported versions

| Version             | Supported     |
| ------------------- | ------------- |
| `main` (pre-v1.0.0) | Best-effort   |
| Any earlier commit  | Not supported |

## Reporting a vulnerability

Send a private email to `info@dineshd.dev` with:

- a short description of the issue,
- steps to reproduce (commit SHA, request payload, expected vs. actual
  behaviour),
- impact in your own words.

Expect an acknowledgement within 72 hours. There is no bounty programme.
Please hold public disclosure until a fix or mitigation has shipped.

## Out of scope

- Volumetric denial-of-service against the unauthenticated demo endpoint.
- Disputes about model accuracy or false-positive rates. Tune your own
  decision threshold.
- Dependency CVEs already tracked upstream; file those with the relevant
  project.
- Issues reproducible only against non-synthetic data.

## Acknowledgements

Researchers who report issues in good faith will be credited in release
notes on request.
