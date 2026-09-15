# Security Policy

## Status

This repository is a pilot implementation. It is not a hardened multi-tenant service and must not be exposed directly to the public Internet.

## Supported Deployment

- Bind services to loopback or a private network. The supplied Compose file publishes only on `127.0.0.1`.
- Set a strong, randomly generated `OSPD_API_TOKEN` outside source control before starting the kernel.
- Terminate TLS and perform user/role authorization at a trusted API gateway. The built-in bearer token is a minimum service boundary, not a complete identity system.
- Run workflow workers with a read-only root filesystem where practical, least-privilege service accounts, resource limits, and isolated working directories.
- Do not mount secrets or unrestricted host filesystems into the kernel or worker containers.

Operational routes fail closed when `OSPD_API_TOKEN` is absent. Execution, job, openEO job, and provenance routes require `Authorization: Bearer <token>`. Discovery, conformance, process descriptions, and Building Block metadata remain public.

## Implemented Controls

- CWL file inputs resolve to existing files inside the repository workspace; traversal and external absolute paths are rejected.
- Execution and provenance requests have configurable size limits.
- Provenance requires a minimal PROV-like shape, uses owner-only file permissions, and retains at most `OSPD_MAX_PROVENANCE_RECORDS` records.
- Job logs are bounded internally and are not returned by the results API.
- Direct service dependencies and Python base-image patch versions are pinned.
- TorchScript models are checksum-verified before loading and require a model card containing publisher and licence information.

## Sensitive Data

Real workflows may contain AOIs, image paths, infrastructure locations, classifications, model details, and provenance. Treat these as potentially sensitive operational data even when they contain no personal data. Configure access, retention, jurisdiction, releasability, backup, and deletion policies for each deployment.

## Known Limitations

- Bearer tokens are service-wide and do not provide user-level authorization, rotation, revocation, or audit identity.
- TLS, encryption at rest, secrets management, quotas, sandboxing, and centralized audit logging are deployment responsibilities.
- `Content-Length` checks should be reinforced by request-size limits at the reverse proxy.
- Pinned direct dependencies do not constitute a complete hash-locked transitive dependency set or SBOM.
- A checksum proves model integrity against an expected value; it does not establish model safety, publisher identity, or fitness for purpose.
- The Process-Type Register is read-only but should still be protected by network policy if its contents are sensitive.

## Reporting a Vulnerability

Report vulnerabilities privately through the GitHub repository's Security Advisories feature. Do not include secrets, sensitive imagery, or operational coordinates in a public issue.