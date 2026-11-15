---
description: Load a complete fictional organisation to explore every module before entering your own data
---

# Exploring with demo data

An empty instance says little about what the platform does. **Load demo data** fills it with a complete, fictional organisation, so you can click through audits, risks and dashboards that already hold realistic content before modelling your own.

## What you get

The demo describes **Halvard Devices**, a fictional maker of connected home devices with a payments subsidiary. It is loaded into its own domain, named after the company, and spans the modules:

- **Governance** — perimeters, organisation objectives, policies and documents, commitments, quick forms and requests.
- **Compliance and risk** — audits on frameworks it loads (ISO 27001, NIS2, PCI DSS, NIST CSF 2.0, IEC 62443-3-3, the CRA…), risk assessments and scenarios, risk acceptances, security exceptions, an EBIOS RM study, quantitative risk studies, threat models.
- **Operations** — assets, applied controls with their owners and ETAs, evidences, recurring tasks, findings, vulnerabilities, incidents, technical postures and workflows.
- **Third parties, privacy and resilience** — entities, solutions, contracts and entity assessments, the record of processing activities, business impact analyses, metrics, and projects.

The modules the demo uses are switched on (for instance **workflows**, **contracts**, **quick forms**, **threat modeling** or **project management**), so the data doesn't stay hidden behind a disabled feature flag. That needs permission to change the global settings; without it, the data is loaded and the flags left as they are.

## Load it

Administrators see the **Welcome to CISO Assistant!** dialog at their first sign-in, while no domain exists yet. Later, open it again with **Get Started** in the top bar. Pick **Load demo data** (_Import a sample environment to explore the platform_); you land on the domains list once it is done.

Loading needs permission to add domains. It is refused when:

- the demo is already loaded — _Demo data is already loaded. Delete the demo domain to load it again._
- another domain already uses the demo's name — _A domain already uses the demo domain name. Rename it to load the demo data._

## Remove it

Delete the demo domain from the domains list: everything the demo created goes with it. You can then load it again, for instance after an upgrade that enriched the dataset.

{% hint style="info" %}
The demo is fictional but realistic. Keep it on a test or evaluation instance, or delete it before going live, so it doesn't mix with your own data in dashboards and exports.
{% endhint %}

## Related

- [Initial setup](initial-setup.md)
- [Feature flags](../configuration/settings/feature-flags.md)
