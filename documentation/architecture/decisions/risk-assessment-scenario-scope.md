# Scope a risk assessment's views with one scenario filter carried in the URL

- Status: Proposed
- Date: 2026-10-26
- Deciders: @nas-tabchiche

## Context

A risk assessment is read through several views: the scenario table, the current and residual matrices, the action plan with its budget overview, analytics and flash mode, and the PDF, CSV and Excel exports. Each view selects its scenarios on its own. Only the scenario table can be filtered, and its filters live in browser storage, so server-side page loads and exports cannot see them.

The views also disagree on what the action plan is. The list includes controls linked to a scenario as existing or additional measures. The exports and flash mode include additional measures only.

Scenario filters and control filters share parameter names (`owner`, `folder`, `created_at`), so one query string cannot carry both unprefixed.

## Decision

We will define a scenario scope: the `RiskScenarioFilter` parameters prefixed with `scenario__` (so `scenario__within_tolerance`), minus those the assessment already fixes (folder, perimeter, risk assessment). Every view of a risk assessment applies it on the backend through that filter set. The action plan shows controls linked to at least one in-scope scenario, under one definition shared by the list, budget, analytics, flash mode and exports, with a link-type parameter (additional, existing, all).

The URL is the source of truth for the scope. The browser keeps a copy per assessment and restores it only when the URL carries no scope, always with a visible notice. A filtered export states its scope on the document.

## Consequences

- Any filter added to `RiskScenarioFilter` becomes a scope filter with no extra work. A view that selects scenarios without going through the scope is a bug.
- The link-type parameter defaults to `all`, which is today's list. Exports called through the API without it will now include existing measures. The UI always passes what the table shows, additional measures by default. The `risk_assessments` filter of the applied controls list keeps its meaning, additional measures, unless a selection or link type is passed.
- The scope bar is its own component. Embedded tables keep their rule of never syncing filters to the URL.
- A filtered matrix, list or report must always say it is filtered.

## Security considerations

Scope parameters only narrow querysets that are already filtered by RBAC, and they reuse the validation of the scenario list endpoint, so they expose nothing that endpoint does not. A shared link carries filter values (choices and object ids), never data. The recipient still needs view rights. The stored copy reveals which assessments a user filtered on that browser, which we accept. Stating the scope on exports guards against a filtered report being read as a complete one.

## Alternatives considered

- **A tolerance-only filter on the action plan.** Answers one request. The next criterion would need another one-off parameter.
- **Reading the scenario table's stored filters from the other views.** Invisible to server-side loads, exports and users.
- **sessionStorage.** Same blind spot, per tab, and not shareable.
- **Filtering matrices in the browser.** Exports would need the same logic again on the server, and the two would drift.
- **`risk_scenarios__` as the prefix.** On controls it names additional measures only, and the scope also has to cover existing ones.
- **Server-side saved views.** A larger feature. It can be built on these parameters later.
