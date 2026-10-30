# Security Policy

Being at the heart of it, Cyber Security is very important to us at intuitem.

Our security commitments are detailed in:

- [Security Assurance Plan](https://intuitem.com/security)
- [Service Level Objectives](https://intuitem.com/service-level-objectives), including fix delays for security vulnerabilities

## Supported Versions

CISO Assistant uses semantic versioning (`MAJOR.MINOR.PATCH`). Minor versions are released every few weeks, and patch versions as needed. Fixes ship as new patch releases of the latest minor version. Functional fixes are not backported to earlier minor versions; security fixes may be, case by case (see below).

| Version                                | Functional fixes (MCO) | Security fixes (MCS) |
| -------------------------------------- | ---------------------- | -------------------- |
| Latest minor of the current major      | ✅                     | ✅                   |
| Earlier minor and major versions       | ❌                     | Case by case         |

- **Functional fixes (MCO)** are only provided on the latest minor version. Users of earlier versions must upgrade to get them.
- **Security fixes (MCS)** are provided on the latest minor version, within the delays set in our [Service Level Objectives](https://intuitem.com/service-level-objectives). Depending on the nature of a security issue, we may also issue a hotfix for earlier versions.
- The same policy applies to the Community and Enterprise editions. The SaaS offering always runs a supported version.

### Supported platforms

| Component        | Supported                                                         |
| ---------------- | ----------------------------------------------------------------- |
| Container images | `linux/amd64`, `linux/arm64`                                      |
| Orchestration    | Docker 27 or later with Docker Compose, or Kubernetes 1.31 or later (Helm chart) |
| Host OS          | Linux distributions supporting Docker; Ubuntu/Debian, CentOS and RHEL LTS versions recommended |
| Database         | PostgreSQL 16 or later, or SQLite                                 |

## Reporting a Vulnerability

If you discover any issue regarding security, please disclose the information responsibly by sending an email to security@intuitem.com and not by creating a GitHub issue. We'll get back to you ASAP and work with you to confirm and plan a fix for the issue.

Please note that we do not currently offer a bug bounty program.

## Security Advisories

As soon as we become aware of a vulnerability or security incident affecting CISO Assistant, we notify our customers and issue a security advisory. When a security fix is released, we publish a security advisory for our users.

Advisories are published as [GitHub Security Advisories](https://github.com/intuitem/ciso-assistant-community/security/advisories) on this repository and referenced in the release notes.

For critical vulnerabilities (CVSS 9.0 or higher), we also notify [CERT-FR](https://www.cert.ssi.gouv.fr/contact/), the French national CERT.
