# CISO Assistant — Product Documentation

CISO Assistant is an open-source GRC (Governance, Risk and Compliance) platform that helps security and compliance teams manage frameworks, controls, assessments, and risk in one place.

This handbook is the living reference for the product — written for two audiences in parallel:

- **End users** (CISOs, GRC analysts, auditors, project managers) who use the platform day-to-day.
- **Implementers** (developers, integrators, automation engineers) who build on top of it via the API, library files, or extensions.

## How this handbook is organised

- **Foundations** — the design philosophy and shared vocabulary that the rest of the platform builds on.
- **Core concepts** — the central objects you work with: domains, perimeters, applied controls, assets, assessments, risks.
- **Features** — a catalogue of shipped capabilities, each one written for both audiences in a single page.
- **API & integrations** — how external systems talk to CISO Assistant.

## Conventions

- Each page leads with **what it is** in one or two sentences, then expands.
- Feature pages follow the template in [`_template.md`](_template.md). Authors copy it when adding a new feature.
- Pages marked _draft_ are placeholders waiting for content — contributions welcome.

## Status

This space is the published mirror of the in-repo `product-docs/` directory on `main`. Edits happen through pull requests. The companion [`/docs/`](https://github.com/intuitem/ciso-assistant-community/tree/main/docs) folder in the repository is internal working material and is not published here.
