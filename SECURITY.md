# Security policy

## Supported versions

Security fixes are applied to the latest `0.1.x` release. Earlier development snapshots are not
supported.

| Version | Supported |
| --- | --- |
| Latest 0.1.x | Yes |
| Earlier snapshots | No |

## Reporting a vulnerability

Please use GitHub's **Security → Report a vulnerability** flow for this repository. Do not file a
public issue for an archive-bypass, path traversal, decompression bomb, provenance forgery, or
other issue that could put users or their artifacts at risk.

Include the affected version or commit, operating system, minimal reproducer, expected audit
result, actual audit result, and whether a crafted TBX is required. You should receive an initial
acknowledgment within seven days. A coordinated disclosure date will be agreed after impact and
remediation are understood.

## Auditor guarantees and limits

The auditor treats every TBX archive as hostile. It checks archive structure before extraction,
enforces byte and compression limits, rejects unsafe paths and duplicate names, verifies exact
manifest membership and hashes, validates schemas, and cross-checks semantic identity. These
checks do not make an artifact scientifically true; they establish integrity and consistency with
its declared claim boundary.
