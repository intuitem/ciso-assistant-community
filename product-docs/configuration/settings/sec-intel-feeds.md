# Security intelligence feeds

CISO Assistant can optionally enrich its vulnerability and security-advisory catalogues by polling external threat-intelligence feeds. These switches control which feeds are active and how the platform reaches them.

All feeds are **off by default** — they make outbound network calls, so opt in deliberately.

## Available feeds

- **KEV feed** (`kev_feed_enabled`) — CISA's [Known Exploited Vulnerabilities](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) list. Tags vulnerabilities that are confirmed to be exploited in the wild so they can be prioritised.
- **EPSS feed** (`epss_feed_enabled`) — FIRST's [Exploit Prediction Scoring System](https://www.first.org/epss/). Attaches a probabilistic exploitation score to each CVE, useful for prioritisation alongside CVSS severity.
- **NVD enrichment** (`nvd_enrich_enabled`) — pulls extra metadata from the [NIST National Vulnerability Database](https://nvd.nist.gov) (CWE mappings, affected configurations, references).

## Network

- **Network timeout** (`network_timeout`) — seconds to wait before giving up on a feed call. Default `30`, range `5`-`120`. Tune up if you're behind a slow egress proxy; tune down if you want feed failures to surface quickly rather than block other work.

## Operational notes

- Enabling a feed doesn't backfill the entire history — feeds are consulted from the moment they're enabled. To enrich historical entries, look for a "refresh" action on the relevant catalog (depends on the feed).
- Feed calls happen in background jobs (Huey workers), so toggling a feed doesn't block the request that saves the settings.
- Outbound HTTPS access to the feed endpoints is required. The platform doesn't ship with mirrored data.
