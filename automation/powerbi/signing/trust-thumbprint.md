# Trusting the signed connector (customer IT runbook)

The signed connector (`CisoAssistant.pqx`) lets users keep Power BI
Desktop's **Recommended** data-extension security level. To load it, the
signing certificate's thumbprint must be registered as trusted on each
workstation (and on gateway machines for scheduled refresh).

The current thumbprint is published with each release on the GitHub
releases page.

| Certificate | Thumbprint | Valid until |
|---|---|---|
| `CN=intuitem CISO Assistant Connector` (2026) | `AAB77C4E62D72D26F1E05AAA46457D90A653541E` | 2029-07 |

## Single workstation (Registry)

Add the thumbprint to
`HKEY_LOCAL_MACHINE\Software\Policies\Microsoft\Power BI Desktop`, value
`TrustedCertificateThumbprints` (`REG_MULTI_SZ` — one thumbprint per line):

```powershell
# elevated PowerShell
$path = "HKLM:\Software\Policies\Microsoft\Power BI Desktop"
New-Item -Path $path -Force | Out-Null
New-ItemProperty -Path $path -Name TrustedCertificateThumbprints `
  -PropertyType MultiString -Value @("<THUMBPRINT>") -Force
```

Multiple thumbprints (e.g. during certificate rotation) are supported: pass
several strings in the array.

## Fleet deployment (Group Policy)

Deploy the same registry value via GPO Registry preferences to the
workstations that use Power BI Desktop, and to the on-premises data gateway
hosts.

Reference: [Trusted third-party connectors in Power BI Desktop](https://learn.microsoft.com/en-us/power-bi/connect-data/desktop-trusted-third-party-connectors)

## Connector placement

- **Desktop**: `Documents\Power BI Desktop\Custom Connectors\CisoAssistant.pqx`
- **Gateway**: the folder configured under *Connectors* in the gateway app
  (default `C:\Windows\ServiceProfiles\PBIEgwService\Documents\Power BI Desktop\Custom Connectors`)
