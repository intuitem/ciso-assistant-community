# Internal entities and entity-based campaigns

Status: draft for review — 2026-08-30

## Context

`tprm.Entity` is already more general than "third party": the builtin main
entity owns the root folder, DORA models subsidiaries and branches as entities
via `parent_entity`, and the model is consumed by EBIOS RM (reference entity,
stakeholders), resilience reporting, and privacy. What is missing is a
first-class internal/external distinction and a home for internal entities in
the product.

Separately, campaigns currently fan out one `ComplianceAssessment` per
perimeter × framework (`CampaignViewSet.perform_create`). Perimeters are a poor
proxy for "who is being assessed"; entities are the right subject.

## Decisions

1. **Entity gets an explicit scope discriminator** (option 3 — explicit field,
   not derived from `parent_entity`, not terminology-based).
2. **Campaigns target entities instead of perimeters.** No mixed campaigns: a
   campaign is either internal or external.
3. **Two menu entries, one model.** The existing campaign capability becomes
   "internal campaigns" (general/compliance area); a new "campaigns" entry in
   the third-party section covers external campaigns. Both are scope-filtered
   views of the same `Campaign` model. (Note: today there is no campaigns item
   in `navData.ts` at all — both entries are additions, gated by the existing
   `campaigns` feature flag, the external one additionally by `tprm`.)
4. **External campaign fan-out creates `EntityAssessment`s** (which wrap a
   ComplianceAssessment in an enclave folder), reusing the existing TPRM
   machinery: enclave folders, representatives → requirement assignment,
   third-party respondent enrollment (BI-RL-TPR).
5. **Entities are managed in Organization.** The Organization section hosts the
   single CRUD surface (all entities, scope column + filter). The third-party
   section keeps a pre-filtered view (scope=external) so TPRM users still see
   their third parties next to solutions/contracts/entity assessments. The
   Django model stays in the `tprm` app — moving it would churn content types,
   permission natural keys and cross-app FKs for cosmetic gain.
6. **Scope transitions are guarded, confirmed actions** (see below).

## Entity model changes

```python
class Scope(models.TextChoices):
    INTERNAL = "internal", _("Internal")
    EXTERNAL = "external", _("External")

scope = models.CharField(
    max_length=10, choices=Scope.choices, verbose_name=_("Scope")
)
```

Default is `external` (model and serializer): every programmatic creation
path today — data wizard, TPRM import, preset executor, DORA — creates third
parties. The UI always sends the value explicitly, preset by the entry point:
Organization → internal, third-party section → external.

### Responsible people: actors, not representatives

`Representative` stays what it is today: an **external** contact record
(email-keyed person, feeds enclave respondent enrollment). Internal entities
instead reference actors, mirroring the perimeter field it replaces:

```python
default_assignee = models.ManyToManyField(
    "core.Actor",
    related_name="entity_default_assignee",
    verbose_name=_("Default assignee"),
    blank=True,
)
```

Like on Perimeter, this is declarative metadata (no fan-out behavior consumes
`Perimeter.default_assignee` today — only forms, tables and data-wizard
import). Users and teams both work natively since Actor wraps either.

### Landing rule: the entity's domain, always (decision 2026-08-31)

An entity's audits live where the entity lives: internal campaign audits are
created in `entity.folder`, with no perimeter link. There is no ownership
resolution, no per-entity configuration, and a launch can never be blocked by
ownership shape. The only validation left: an internal campaign target must
live in a DOMAIN folder (the main entity lives in the root folder and is
therefore not targetable).

Consequences accepted with this rule:

- Generated audits carry no `perimeter` FK, so perimeter-scoped analytics do
  not count campaign audits. Perimeters stop being a campaign concept.
- Entities sharing a domain get their audits side by side in that domain,
  differentiated by name (`campaign - entity - framework`) and the campaign's
  audit list, not by structure. Give each BU its own domain if separation
  matters.

Along the way (2026-08-31): **`owned_folders` was removed from Entity** and
the main entity is now marked by an explicit **`is_main` boolean** (partial
unique constraint `unique_main_entity`), replacing the implicit
"builtin + owns the root folder" convention. `owned_perimeters` (an earlier
iteration of this design) was never shipped. The orphaned `owned` filter on
the folders endpoint was removed with the field; the serdes domain import
keeps popping `owned_folders` so pre-removal export files still import.
`scope` stays a two-value enum rather than a boolean: it is a taxonomy (and
symmetric with `Campaign.target_scope`), not a feature flag, and an enum can
absorb a third category without a breaking migration.

Consequences:

- Representative creation/update is validated against the entity's scope:
  refused on internal entities (loud error, camelCase i18n key).
- UI: internal entity detail shows Default assignee; external entity detail
  shows Representatives (default_assignee stays available if a use appears
  later, e.g. an internal relationship owner for a third party, but is not
  surfaced at v1).

### Migration defaults

- Main entity (`get_main_entity()`) → `internal`.
- Every entity reachable from the main entity via `parent_entity` (recursive)
  → `internal` (covers DORA subsidiaries and branches).
- Everything else → `external`.

### Scope is immutable (decision 2026-08-31)

`scope` is fixed at creation and can never be edited
(`entityScopeIsImmutable`; the form disables the select on edit). This
supersedes the earlier guarded-transition design: in the rare case an entity
truly changes nature, the user creates a new entity of the other scope and
copies the relevant information. Immutability makes all transition guards
(campaign locks, branch checks, main-entity protection) unnecessary — nothing
that references an entity can ever see its scope change.

## Campaign model changes

```python
class TargetScope(models.TextChoices):
    INTERNAL = "internal", _("Internal")
    EXTERNAL = "external", _("External")

target_scope = models.CharField(max_length=10, choices=TargetScope.choices)
entities = models.ManyToManyField("tprm.Entity", related_name="campaigns")
# perimeters M2M: kept read-only for legacy campaigns, no new writes (see migration)
```

Validation at creation:

- `entities` must be non-empty and every entity's `scope` must equal
  `target_scope` (loud error listing mismatches, no silent filtering);
- `target_scope` is immutable after creation;
- entity pickers filter on the campaign's scope.

The two nav entries preset and filter `target_scope`:

- existing/general campaigns menu → `target_scope=internal`;
- new entry under `thirdPartyCategory` → `target_scope=external`.

### Internal fan-out

Per entity × framework, create a `ComplianceAssessment` (as today), named
`{campaign} - {entity} - {framework}`, **with `authors` set from the entity's
`default_assignee` actors**.

This is the core purpose of the campaign feature: assign dozens of audits to
the right people in one action, so they appear in each person's "my
assignments" (which filters on `authors`/`reviewers`). Note this fixes a gap
on current main: the perimeter fan-out creates audits with empty `authors`,
and nothing ever reads `perimeter.default_assignee`, so campaign audits reach
nobody. It also mirrors the external side, where the EntityAssessment flow
already sets `audit.authors` from representative actors
(`_finalize_linked_audit`).

Entities with an empty `default_assignee` are accepted (audit created
unassigned); the entity picker's help text states the assignment behavior
(a pre-submit "these entities have no assignee" hint is a possible follow-up).

**Landing:** `folder = entity.folder`, `perimeter = None` — see "Landing
rule: the entity's domain, always" above. The only check: the entity's
folder must be a DOMAIN (`campaignEntityFolderMustBeDomain` otherwise).

### External fan-out

Per entity × framework, create an `EntityAssessment` with the equivalent of
`create_audit=True`: the existing serializer flow builds the enclave folder,
the ComplianceAssessment inside it, requirement assessments, and the
representative→respondent wiring. The campaign form for external scope exposes
the fields that flow needs (framework(s), implementation groups, due date;
respondent setup stays per-entity-assessment afterwards, as today).

`EntityAssessment.folder` = campaign folder; `perimeter` stays optional
(enclave audits carry no perimeter).

### Migration of existing campaigns

Existing campaigns are perimeter-based. To preserve them:

1. For each perimeter referenced by at least one campaign, create an internal
   entity: `name = perimeter.name`, `folder = perimeter.folder`,
   `scope=internal`, `builtin=False`. Reuse one entity per perimeter across
   campaigns. Because the entity lives in the perimeter's folder, the landing
   rule keeps future audits in the same domain as today (the `perimeter` FK
   itself is intentionally no longer set — no remaining perimeter linkage).
2. Carry responsibility over actor-to-actor: copy
   `perimeter.default_assignee` into `entity.default_assignee` verbatim.
   No `Representative` rows are created — representatives are external-only.
   Users, teams, and repeated assignees across perimeters all work without
   special cases (no email-uniqueness constraint involved).
3. Set `campaign.target_scope = internal` and populate `campaign.entities`
   with the created entities.
4. Keep `campaign.perimeters` rows untouched for provenance; the field
   becomes read-only (dropped in a later release).

Migration must be checked against PostgreSQL (not only SQLite).

The same migration pass also stamps `is_main=True` on the entity matching the
legacy main-entity convention (builtin + owns the root folder) before
`owned_folders` is dropped in the follow-up migration.

## UX summary

- Organization section: "Entities" points to `/entities?scope=internal` —
  internal entities only. The entity form presets scope from the `?scope=`
  URL param, locks it on edit (scope is immutable), and shows the default
  assignee picker for internal entities. The main entity carries a star icon
  next to its name in list views (tooltip: "Main entity").
- Third-party section: "Entities" points to `/entities?scope=external` — the
  same route/table, pre-filtered; creation there presets scope=external.
  Each section manages only its own scope.
- Campaigns: the existing (EE) campaigns entry becomes
  `/campaigns?target_scope=internal`; a new third-party entry points to
  `/campaigns?target_scope=external`. The form presets and locks
  `target_scope` (immutable on edit), filters the entity picker by scope, and
  clears the selection when the scope flips. Campaign detail lists generated
  audits (internal) and entity assessments (external, via the
  `compliance_assessment__campaign` filter).

## Out of scope / later

- Removing `campaign.perimeters` (after a deprecation cycle).
- Moving the Entity model out of the `tprm` Django app (accepted debt).
- Internal-entity org-chart features beyond `parent_entity` (departments,
  BUs as a tree UI).
- Extending EBIOS RM stakeholder terminology with internal relationship types.

## Settled questions

- External campaigns are multi-framework at v1 (entities × frameworks matrix,
  symmetric with internal). (2026-08-30)
- The third-party Entities view allows creation, preset `scope=external`.
  (2026-08-30)
- Internal landing: the entity's own domain, always — superseding the earlier
  strict single-owned-target rule, which was impractical for entities owning
  several domains/perimeters. (2026-08-31)
- Internal fan-out sets `authors` only; reviewers stay manual at v1.
  (2026-08-30)
- No interim perimeter fix on main — the redesign ships the assignment
  behavior directly. (2026-08-30)
- `owned_folders` removed; main entity marked by `is_main` boolean, shown as
  a star icon (tooltip "Main entity") next to the name in list views — a
  symbol rather than text, to avoid long translations. (2026-08-31)
- Entity `scope` stays a two-value enum, not a boolean. (2026-08-31)
- Scope is immutable after creation (copy into a new entity for the rare
  genuine change); Organization manages internal entities only, the
  third-party section external only. (2026-08-31)
- Scope is implicit in each view: the `?scope=` / `?target_scope=` URL params
  are enforced as ModelTable `overrideFilters` (declared per model via
  `lockedFilters` in crud.ts, wired in the generic list page). Overrides take
  precedence over filter state and survive "reset filters"; the fields are
  also declared `hide: true` so no chip is ever shown. A first hide-only
  attempt was rejected as fragile — reset cleared it. (2026-08-31)
- No scope column in the entities list and no scope row in the detail view —
  the section implies it, and the generic `scope` i18n key translates to
  "Périmètre" in French, colliding with the Perimeter concept. The creation
  form's select uses a dedicated `entityScope` key (FR "Portée"). (2026-08-31)
