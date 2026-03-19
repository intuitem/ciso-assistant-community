---
title: Cryptography & Encryption Policy
description: Standards for the use of cryptographic controls and encryption to protect information
---

# Cryptography & Encryption Policy

## 1. Purpose

This policy defines the requirements for the use of cryptographic controls to protect the confidentiality, integrity, and authenticity of information within [Organization Name].

## 2. Scope

This policy applies to all systems, applications, and data owned or managed by [Organization Name], including data at rest, data in transit, and data in use.

## 3. Encryption Standards

### 3.1 Data at Rest

- All sensitive and confidential data stored on servers, databases, and storage media must be encrypted.
- Full-disk encryption must be enabled on all endpoints (laptops, workstations, mobile devices).
- Approved algorithms: AES-256 for symmetric encryption.

### 3.2 Data in Transit

- All network communications carrying sensitive data must use encrypted channels.
- TLS 1.2 or higher is required for all web and API communications.
- Legacy protocols (SSL, TLS 1.0, TLS 1.1) are prohibited.
- VPN connections must use approved encryption standards for remote access.

### 3.3 Data in Use

- Where technically feasible, application-level encryption should be used for processing sensitive data.
- Database field-level encryption should be applied to highly sensitive fields (e.g., authentication credentials, financial data).

## 4. Key Management

### 4.1 Key Generation

- Cryptographic keys must be generated using approved random number generators.
- Key lengths must meet or exceed current industry recommendations.

### 4.2 Key Storage and Protection

- Private keys must never be stored in plaintext.
- Hardware security modules (HSMs) or equivalent key management services should be used for critical keys.
- Access to cryptographic keys must be restricted to authorized personnel only.

### 4.3 Key Rotation and Expiry

- Encryption keys must be rotated according to a defined schedule based on risk assessment.
- Compromised or suspected-compromised keys must be revoked and replaced immediately.
- Expired keys must be securely archived or destroyed according to retention requirements.

### 4.4 Key Destruction

- Keys that are no longer needed must be securely destroyed using approved methods.
- Key destruction must be documented and auditable.

## 5. Certificate Management

- Digital certificates must be issued by trusted certificate authorities.
- Certificate expiration must be monitored, and renewals must be completed before expiry.
- Self-signed certificates are prohibited in production environments.

## 6. Prohibited Practices

- Use of proprietary or unvetted encryption algorithms is prohibited.
- Hardcoding encryption keys in source code is prohibited.
- Transmission of encryption keys via unencrypted channels is prohibited.
- Disabling or bypassing encryption controls without documented approval is prohibited.

## 7. Roles and Responsibilities

- **IT Security Team**: Define encryption standards, manage key infrastructure, and conduct compliance reviews.
- **System Administrators**: Implement and maintain encryption on systems and infrastructure.
- **Developers**: Apply encryption standards in application development and ensure secure key handling.
- **All Employees**: Comply with encryption requirements for data handling and device usage.

## 8. Compliance

Violations of this policy may result in disciplinary action up to and including termination. Non-compliance may also expose [Organization Name] to legal and regulatory penalties.

## 9. Policy Review

This policy shall be reviewed at least annually or upon significant changes to the threat landscape, technology environment, or regulatory requirements.
