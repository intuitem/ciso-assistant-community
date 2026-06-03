---
description: Fuzzy search across every searchable object in the workspace
---

# Universal search

The **universal search** is a single full-workspace query that returns matches across every searchable object type — assets, audits, applied controls, evidences, frameworks, risk scenarios, third-party entities, EBIOS RM artefacts, vulnerabilities, and many more — in one ranked, grouped list.

Matching is **fuzzy and accent-insensitive**, so you can mistype, drop accents, or only half-remember the exact wording and still land on the right object. It's the answer to "where is _that thing_ I half-remember?" without having to guess which page to land on first.

## How to open it

Three entry points, all converging on the same `/search` results page:

- **From the [command palette](command-palette.md)** — open the palette (`⌘K` / `Ctrl+K`), type your query, and press `↵`. When the text doesn't match a sidebar destination, the palette falls through to the search page.
- **Direct URL** — `/search?q=<your query>`.
- **From within the search page itself** — once you're on `/search`, the top bar input runs subsequent queries.

You need at least **2 characters** for a query to be processed — single-character searches return empty so the platform doesn't fan out a match-everything query across every table.

## What gets searched

Universal search covers an explicit registry of object types in the backend (`SEARCHABLE_MODELS`). The current set spans:

| Area | Object types |
|---|---|
| Organisation | Domains, Perimeters |
| Catalogue | Frameworks, Threats, Reference controls, Risk matrices, Requirements |
| Assets | Assets, Vulnerabilities |
| Operations | Applied controls, Policies, Incidents, Findings, Security exceptions, Task templates, Evidences |
| Governance | Risk acceptances |
| Risk | Risk assessments, Risk scenarios |
| Compliance | Audits |
| Third-party risk | Entities, Solutions, Contracts |
| EBIOS RM | Studies, Feared events, Strategic scenarios, Attack paths |
| Privacy | Processings, Data breaches, Right requests |
| Resilience | Business impact analyses |

For each model, the search looks at the **name**, **description**, and (where it applies) the **reference ID** — plus a handful of cross-joined fields where they help (`risk_scenario.risk_assessment.name`, `compliance_assessment.framework.name`, `solution.provider_entity.name`, `threat.provider`).

## Fuzzy and accent-insensitive matching

You don't need to type an object's name exactly to find it.

- **Fuzzy scoring.** Every candidate is scored against your query with a fuzzy-matching algorithm (rapidfuzz), so `firewal polcy` still surfaces _Firewall policy_, and a partial query like `iso 270` still surfaces _ISO 27001 audit_. Higher-scoring matches sort first, and the height of the small bar on the left of each result is a visual cue for the score.
- **Accent-insensitive.** Diacritics are normalised on both sides of the comparison. Typing `referentiel` matches `référentiel`, `securite` matches `sécurité`, and `protege` matches `protégé` — so francophone, hispanophone, lusophone, and similar workspaces don't get punished for typing without accents.
- **Case-insensitive.** Capitalisation is ignored: `firewall`, `Firewall`, and `FIREWALL` are equivalent.

This is intentionally generous. The cost of an extra near-miss in the result list is small; the cost of failing to find an object because of a typo or a missing accent is much higher.

{% hint style="info" %}
Results are filtered by the **same IAM scoping** as everything else: you only see objects in domains you have access to. If [Focus mode](focus-mode.md) is engaged, results are further restricted to the focused sub-tree.
{% endhint %}

## Reading the results

The page renders matches **grouped by object type**, with a coloured accent and an icon per group. Each row shows:

- The object **name** as the headline.
- A **reference ID** chip (when the object carries one).
- The **domain** the object lives in (sitemap icon).
- A short **description** if one is set.
- A **score bar** on the left — a vertical fill that grows with the match score, giving you a quick visual sense of how well each result matches.

Across the top, **type filter chips** let you narrow the result list to a single object type with one click: _All_, then one chip per type present in the current result set, each carrying its own count. Click a chip to toggle that filter on; click it again — or click _All_ — to clear it.

## Keyboard controls

The results page is designed for keyboard navigation:

| Key | Action |
|---|---|
| `/` | Focus the search input (from anywhere on the page) |
| `↓` or `j` | Move selection down |
| `↑` or `k` | Move selection up (releases focus back to the input at the top of the list) |
| `↵` (Enter) | Open the selected result |
| `Esc` | Clear the current selection |

Hovering a row with the mouse also moves the selection, so `↵` always opens the visually-highlighted row regardless of how you got there.

## Why use it

- **Cross-domain lookup** — finding an applied control without first remembering which domain owns it.
- **Half-remembered names and typos** — fuzzy scoring rescues "the SOC2 evidence about… backups? logs?" and forgives the occasional mistyped character.
- **Cross-language workspaces** — accent-insensitivity means French, Spanish, Polish, and similar workspaces don't get penalised for typed-without-accents queries.
- **Reference IDs** — looking up `ISO-27001-A.5.1.1` or a custom internal ref code goes straight to the object.

## Related

- [Command palette](command-palette.md) — the primary entry point and the page-jump UI it lives next to.
- [Focus mode](focus-mode.md) — narrows search results to a single domain sub-tree when engaged.
- [Understanding the IAM model](../configuration/organization/iam-model.md) — why some objects don't appear in your results.
