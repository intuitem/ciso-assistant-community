# Reports, exports and charts read through one scope object, and a canary test proves it

- Status: Proposed
- Date: 2026-11-11
- Deciders: @eric-intuitem
- Related: [derived-metrics-from-workflow-reads](derived-metrics-from-workflow-reads.md) (the shared read layer), [full-view-permissions](full-view-permissions.md)

## Context

A user may view an object only through a role that gives `view_<model>` on the object's folder. The list and detail endpoints apply this twice: `BaseModelViewSet.get_queryset` keeps the rows the user can view, and the masking of related objects replaces each linked object the user cannot view with `{}`. Links are first-class since the link rule: an object may link objects in other domains, the interface counts the hidden ones, and an edit keeps them.

Everything that builds its own response reads the database directly instead: CSV and XLSX exports, generated documents (PDF, Word, Markdown), archives, charts, graphs and analytics. There the view check is a line each author must remember to write. `core/views.py` holds about a hundred hand-written `get_viewable_object_ids` filters; `core/generators.py` and the domain export hold none. A review of these responses found some forty that return or name objects the caller cannot view: a row's links are followed with `.all()`, and a few responses select whole objects with no filter at all, attachment files included. Fixing them one by one leaves the cause in place: the next export will be written the same way.

The code already contains the answer twice. `core.reads.ReadScope` serves workflows and derived metrics: its documentation says "there is no unscoped read", it narrows every queryset, and it prefetches related objects with the same filter. `chat.scoping.ReadScope` serves the chat: it resolves what a user may read per model, caches it for the request, and exists "so it can never return more than the API would". Several other places work the same thing out again for themselves (`_get_accessible_ids_map`, `_masked_reader`, `linked_findings_filter`, the domain quality rules, `core/neighborhood.py`).

## Decision

We will give reporting one way to read: a scope object built once per request for the requesting user, and we will forbid reporting code from reaching the database any other way.

The scope answers two questions. *Rows*: the objects of a model the user can view. *Links*: the objects linked to a row, as the ones the user can view plus the number they cannot. It works each model out once per request, and it applies the respondent rules where the API does. It is `core.reads.ReadScope`, extended with a constructor for a user's whole reach; the chat's class is folded into it.

Reporting code receives the scope and declares what it reads. An export column names a relation; the export resolver follows each hop through the scope and prints the visible objects followed by the count of hidden ones, in the words the interface already uses. A document's context and a chart's data are built from scoped rows and scoped links the same way. No reporting module calls `Model.objects` or a relation's `.all()`.

One generic test guards it. For every GET route and every link a model declares, it places a canary object in a domain the test user cannot view, calls the route, and fails if the canary's name appears in the response, whatever its format. A new route is covered the day it is added. Exemptions are listed in the test, each with its reason.

The write side is not scoped. Checking and saving an edit must see hidden links to keep them and to count them, so no filter is added to model managers or to the database.

## Consequences

- **The canary test comes first.** It ships with the responses that fail today listed as known failures. That list is the backlog of this decision: it may only shrink.
- **Then the scope and the generic export resolver**, which closes every list export in one place. Documents, archives and charts follow, one family at a time (audit, risk, follow-up and incident, business impact, EBIOS RM, quantitative risk, third parties, domain export).
- **No response is patched ahead of its family.** This includes the ones that return whole objects or attachment files (the domain export, the audit export archive, the action plan files): they have behaved this way for several releases, and they are fixed where the cause is removed.
- **Effect on API clients.** List and detail responses do not change. In exports, documents and charts, an object the caller cannot view is left out when it is a row, and counted instead of named when it is a link. A client that can view everything sees no difference.
- **Required:** the domain export refuses, with a message, when it would contain objects the caller cannot view. An export that silently leaves objects out cannot be imported faithfully.
- **Required:** a report never receives a model instance it could walk. It receives scoped rows and scoped links.
- **Required:** a number computed over objects the viewer cannot see is written as an explicit aggregate, where the product already accepts one. It is never obtained by reading the rows.
- **Required:** the scope is built from the authenticated user and nothing else. No request parameter widens it.
- **Fewer queries.** What a user may view is worked out once per model per request, where each response part works it out again today.
- **The ad-hoc copies go.** As each family moves, its own view filters and masking helpers are removed; `_filter_related_fields` stays for serializer output and takes its allowed ids from the scope.
- **Harder:** a quick export can no longer be three lines over the ORM. That is the point.

## Security

**Conclusion: the decision removes a class of exposure and adds none.** It takes the two checks the lists already apply and makes them the only way reporting can read. No permission, role or scope of any user changes.

### Why a report cannot show more than the lists

1. **Rows.** A report gets rows from the scope only, and the scope uses `get_viewable_object_ids`, the rule `BaseModelViewSet.get_queryset` uses. A row the list would not show cannot reach a report.
2. **Links.** A report gets linked objects from the scope only, with the same rule applied to the linked model. A link the detail view would mask is counted, not named.
3. **No other way in.** A check on the reporting modules fails the build when one of them calls `Model.objects` or a relation's `.all()`.
4. **Every route is tested, including the next one.** The canary test enumerates routes and links from the code itself, so nobody has to remember to add a case. An untested route is one listed as exempt, with a reason a reviewer can read.
5. **The scope cannot be widened from outside.** It is frozen once built and takes its identity from the authenticated request.
6. **Writes are untouched.** The checks on linking and editing stay as they are, so nothing a user could not write before becomes writable.

### Remaining risks, accepted as low

- **A count reveals that hidden links exist.** The interface already shows this count on every detail page.
- **Aggregates over objects the viewer cannot see** stay where the product accepts them today. They are numbers, written as such.
- **PDF output is checked on its context, not on the rendered file.** A custom template receives the same trimmed context, so it cannot print what the context does not hold.
- **Text that embeds another object's name is not a link.** A stakeholder's label is its entity's name, and an object's path names its parent folders. The scope does not see these; each needs its own ruling.
- **Until a family has moved, its responses behave as on main.** The known-failure list says exactly which.

### What would change this assessment

Reporting code that reads the database directly, an exemption added to the canary test without a reason, a scope that takes its user or its folders from request parameters, or implicit filtering added to the write side: each reopens the question and requires a new decision.
