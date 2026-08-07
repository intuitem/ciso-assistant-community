# Generating the connector signing certificate

The connector is signed with a project self-signed code-signing certificate
(3-year validity). Customers trust its thumbprint explicitly — see
[trust-thumbprint.md](trust-thumbprint.md).

## One-time generation (Windows PowerShell, elevated not required)

```powershell
$cert = New-SelfSignedCertificate `
  -Type CodeSigningCert `
  -Subject "CN=intuitem CISO Assistant Connector" `
  -KeyAlgorithm RSA -KeyLength 4096 `
  -HashAlgorithm SHA256 `
  -NotAfter (Get-Date).AddYears(3) `
  -CertStoreLocation Cert:\CurrentUser\My

# Export as password-protected .pfx
$pwd = Read-Host -AsSecureString "PFX password"
Export-PfxCertificate -Cert $cert -FilePath CisoAssistantConnector.pfx -Password $pwd

# Record the thumbprint (this is what customers whitelist)
$cert.Thumbprint
```

## Storage

- `CisoAssistantConnector.pfx` and its password are **never committed**.
- GitHub Actions secrets on this repository:
  - `PBI_SIGNING_CERT` — the `.pfx` base64-encoded
    (`[Convert]::ToBase64String([IO.File]::ReadAllBytes("CisoAssistantConnector.pfx"))`)
  - `PBI_SIGNING_PASSWORD` — the password
- Keep an offline copy of the `.pfx` in the team vault.

## Signing (what CI does)

```powershell
MakePQX pack -mz CisoAssistant.mez -t CisoAssistant.pqx
MakePQX sign CisoAssistant.pqx --certificate CisoAssistantConnector.pfx --password <pwd> --replace
MakePQX verify CisoAssistant.pqx
```

`MakePQX.exe` comes from the `Microsoft.PowerQuery.SdkTools` NuGet package.
`verify` reports `"Status": "UntrustedRoot"` for a self-signed certificate —
that is expected; validity is established client-side via the thumbprint
policy.

## Rotation

Certificate expires 3 years after generation. On rotation: generate a new
certificate, update both GitHub secrets, publish the new thumbprint in the
release notes and update trust-thumbprint.md — customers must add the new
thumbprint (keeping the old one during transition is fine, the registry
value accepts a list).
