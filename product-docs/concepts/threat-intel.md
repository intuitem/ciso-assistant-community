---
description: Catalogued vulnerabilities, weaknesses, and the feeds that enrich them
---

# Threat intelligence

The **threat intelligence** layer holds the catalogued knowledge CISO Assistant uses to prioritise vulnerabilities, qualify incidents, and connect operational findings to the wider security ecosystem. Today it covers security advisories, weakness catalogues, and a small set of public enrichment feeds; the surface is expected to grow significantly in upcoming releases.

## Security advisories

A **security advisory** is a catalogued security warning published by a vendor, CERT, or standards body. CISO Assistant supports four sources today:

- **CVE** — the MITRE/NIST CVE Program identifiers (`CVE-YYYY-NNNN`).
- **EUVD** — the EU Vulnerability Database (post-NIS2 European equivalent).
- **GHSA** — GitHub Security Advisories.
- **Other** — for sources that don't fit the above.

Each advisory carries the usual identifying metadata (reference ID, published date, references) plus the bits that drive prioritisation:

- **CVSS base score** and **CVSS vector** — severity per the standard scoring system.
- **EPSS score** and **EPSS percentile** — probabilistic exploitation likelihood from FIRST.
- **Active exploitation flag** and the **KEV date** when the advisory landed on CISA's Known Exploited Vulnerabilities list.
- **Aliases** — cross-references to other identifiers when an advisory exists under multiple IDs.

Advisories are catalog objects: library-backed, root-folder-published, referenced from vulnerabilities and assets rather than re-created per scope.

## CWEs

The **Common Weakness Enumeration** is MITRE's catalogue of software-weakness categories — buffer overflows, missing authentication, improper input validation, and so on. Where a security advisory is "this _specific_ vulnerability in this _specific_ product", a CWE is "this _class_ of flaw". CWEs are catalogued separately and tagged onto advisories and vulnerabilities to enable categorical analysis ("how many of our open vulns are credential-handling bugs?").

CWEs ship as their own catalog library; loading the CWE library makes the entries available across the platform.

## How they connect to vulnerabilities

A **vulnerability** in CISO Assistant is the organisation-specific record — "we have this exposed in our environment, here's the SLA". It links to:

- One or more **security advisories** — the upstream finding(s) it corresponds to.
- One or more **CWEs** — the weakness categories it belongs to.

This linkage is what lets enrichment feeds work end-to-end: advisories get scores from EPSS, exploitation status from KEV, and category mappings from NVD; vulnerabilities inherit that context via their advisory links and surface it in dashboards and SLA prioritisation. See [Vulnerabilities](vulnerabilities.md).

## Enrichment feeds

Three public feeds enrich the catalogue when enabled — they keep the threat-intel layer current without manual data entry. Configuration is under [Security intelligence feeds](../configuration/settings/sec-intel-feeds.md):

- **KEV feed** — CISA's Known Exploited Vulnerabilities; flags advisories under active exploitation.
- **EPSS feed** — FIRST's Exploit Prediction Scoring System; attaches a probabilistic exploitation score.
- **NVD enrichment** — pulls extra metadata from the NIST National Vulnerability Database (CWE mappings, affected configurations, references).

Each feed is a separate flag and can be toggled independently. The platform stores feed status, network timeout, and last-update timestamps centrally.

## Where this is going

The threat-intelligence surface is being expanded to cover full STIX-style threat intelligence — threat actors, attack patterns, indicators of compromise, campaigns, sightings — along with STIX 2.1 / TAXII / MISP / OpenCTI interop and DORA cyber-threat notification workflows. The objects on this page remain the entry point; new SDOs will sit alongside them.

## Related

- [Vulnerabilities](vulnerabilities.md)
- [Incidents](incidents.md)
- [Security intelligence feeds](../configuration/settings/sec-intel-feeds.md)
- [Vocabulary → Security advisory / CWE](../introduction/vocabulary.md)
