# Field Label Customization — Design Note

## Summary

Some customers want to **rename a field** to match their own vocabulary — e.g.
display "Qualifications" as **"Risk category"** everywhere it appears. Today the
terminology mechanism lets them customize a field's *values*, but not the
field's own *name*.

This note proposes a small **field-label override layer**, anchored on the same
`FieldPath` enum terminologies already use, that lets an instance relabel a
fixed set of fields. It is a **new mechanism**, not an extension of the
per-option `Terminology` row.

## Problem: why terminologies can't do this today

A `Terminology` row is a single **option** (e.g. "confidentiality"). Its
`field_path` (`backend/core/models.py:1936`) is only a *grouping key* saying
which field's dropdown an option belongs to:

- Backend: `limit_choices_to={"field_path": "qualifications", ...}` on the M2M
  (`FearedEvent`, `Incident`, `RiskScenario`, `EscalationThreshold`).
- Frontend: `optionsEndpoint="terminologies?field_path=qualifications&is_visible=true"`.

There is **no terminology row that represents "the qualifications field" as a
whole**, so there is nothing to hang a field-name override on. And the label
itself never comes from terminologies:

- **Frontend label** → static Paraglide message `m.qualifications()`
  (`frontend/messages/en.json:2053`). Compiled at build time into
  `src/paraglide/`. ~9 direct call sites plus generic table/detail rendering.
- **Backend label** → hardcoded `verbose_name="Qualifications"` on each M2M
  field. This is cosmetic (DRF/admin metadata); it is **not** the user-facing
  label, so the feature can largely ignore it.

## How labels are resolved in the frontend (the two paths)

Understanding this is the crux — a relabel feature must reach *both*:

1. **Generic path — `safeTranslate(key)`** (`frontend/src/lib/utils/i18n.ts:102`).
   Used for table column headers and generic detail fields. It resolves a field
   key via `m[toCamelCase(key)](...)`. This is the natural chokepoint: one
   change here relabels every generically-rendered occurrence.

2. **Direct path — `m.qualifications()`** hardcoded in specific components:
   - `Forms/ModelForm/FearedEventForm.svelte:80`
   - `Forms/ModelForm/IncidentForm.svelte:130`
   - `Forms/ModelForm/QuantitativeRiskScenarioForm.svelte:116`
   - `Forms/ModelForm/EscalationThresholdForm.svelte:58`
   - `risk-scenarios/[id]/edit/+page.svelte:580`, `risk-scenarios/[id]/+page.svelte:559`
   - `ebios-rm/[id]/report/+page.svelte:310`,
     `quantitative-risk-studies/[id]/executive-summary/+page.svelte:323`

   These bypass `safeTranslate` and must be routed through the new resolver.

## Design decision

**Anchor on `FieldPath`, not on `Terminology` rows.** `FieldPath`
(`backend/core/models.py:1936`) already enumerates exactly the set of
customizable field slots. A field label is a property *of the slot*, so:

- Store **one label override per `field_path`**, with translations — mirroring
  the `translations` JSON shape terminologies already use.
- Keep it a **separate concern** from `Terminology` (which stays "options").
  Reusing the option table for a field-descriptor would overload row semantics
  and complicate `limit_choices_to` / uniqueness.

**Scope: global (instance-wide), not per-folder.** Deployments are
single-tenant; a customer expects "rename this field" to apply everywhere, not
per domain. This keeps resolution synchronous and cache-friendly (no per-object
folder lookup on every label render).

**One signal, one meaning.** This layer only overrides *display names*. It does
not add fields, does not change `field_path` values, and does not touch
terminology option behavior.

## Proposed backend

New model (sketch), living beside `Terminology` in `backend/core/models.py`:

```python
class FieldLabelOverride(models.Model):
    field_path = models.CharField(
        max_length=100,
        choices=Terminology.FieldPath.choices,
        unique=True,                      # one override per slot
    )
    name = models.CharField(max_length=200)          # default-locale label
    translations = models.JSONField(default=dict)    # {"fr": {"name": "..."}}, like Terminology
    is_active = models.BooleanField(default=True)

    def get_name_translated(self):       # mirror Terminology.get_name_translated
        ...
```

Notes:
- `unique=True` on `field_path` gives a clean upsert per slot.
- No `FolderMixin` — global scope by decision above.
- `translations` reuses Terminology's JSON convention so the frontend/serializer
  helpers are consistent.

**Serializer / viewset**: a thin read+write pair and a `FieldLabelOverrideViewSet`
registered at `field-label-overrides`, filterable on `field_path`. Read payload:
`{ field_path, name, translated_name, is_active }`.

**Delivery to the client**: labels are needed on nearly every page, so expose
the active overrides in a **single global fetch** rather than per-component.
Candidates:
- add them to the existing global/client-settings bootstrap payload, **or**
- a dedicated cached `GET /field-label-overrides/active` returning
  `{ "<field_path>": "<translated_name>" }`.

Prefer folding into the existing global settings load so there is no extra
round-trip on every navigation.

## Proposed frontend

Introduce a single resolver that both label paths go through:

```ts
// resolves a field key to its label, honoring instance overrides
export function fieldLabel(key: string, params = {}, options = {}): string {
    const override = getFieldLabelOverride(key);   // from global store, locale-aware
    return override ?? safeTranslate(key, params, options);
}
```

Then:
1. **Generic path** — have `safeTranslate` (or a wrapper it delegates to)
   consult the override store first, so all table/detail rendering picks it up
   for free.
2. **Direct path** — replace the ~9 hardcoded `m.qualifications()` calls with
   `fieldLabel('qualifications')`. (A quick follow-up cleanup: discourage new
   direct `m.<field>()` calls for override-eligible fields.)

The override store is populated once from the global fetch above and re-resolves
on locale change (Paraglide language switch).

## Defaults, seeding, back-compat

- **No default rows.** With no override present, `fieldLabel` falls back to the
  existing Paraglide message — identical to today's behavior. Zero-risk default.
- **Seeding** is unnecessary; the feature is opt-in per customer. If an admin UI
  is desired, it can list `FieldPath.choices` and let the user set a label per
  slot (empty = use default).
- **Migration**: one additive migration for the new table. No data migration;
  no change to existing terminology rows.
- **`verbose_name`** on the models is left as-is. If backend-emitted labels ever
  surface to users (exports, admin), a later pass can route those through the
  same override — out of scope here.

## Admin surface (optional, phase 2)

A management screen mirroring the Terminology screen: list the `FieldPath`
slots, show current label + default, edit `name` + `translations`, toggle
`is_active`. Root-only (global config), consistent with other instance-wide
settings.

## Open questions

1. **Which fields are relabel-eligible?** All of `FieldPath`, or an explicit
   allowlist? Starting with all `FieldPath` slots is simplest and matches the
   "these are the customizable slots" intent.
2. **Singular vs plural / column vs form label.** `m.qualifications()` (plural)
   and `m.qualification()` (singular) are distinct keys. Does an override need
   both forms, or is one label acceptable everywhere? (Likely one is fine for a
   first cut.)
3. **Delivery mechanism** — fold into global settings payload vs dedicated
   cached endpoint. Recommend global settings to avoid an extra request.
4. **Backend labels** (exports/admin) — in scope now or deferred? Recommend
   deferred; the user-facing surface is the frontend.

## Implementation checklist

- [ ] Backend: `FieldLabelOverride` model + migration (`backend/core`).
- [ ] Backend: read/write serializers + viewset + URL registration.
- [ ] Backend: include active overrides in the global settings payload
      (or dedicated cached endpoint).
- [ ] Frontend: override store hydrated from the global payload, locale-aware.
- [ ] Frontend: `fieldLabel()` resolver; wire `safeTranslate` to consult it.
- [ ] Frontend: replace the ~9 direct `m.qualifications()` call sites.
- [ ] (Phase 2) Admin screen to manage overrides, root-only.
- [ ] Docs: note the feature and its global scope.

## Non-goals

- Adding new fields via configuration (only relabeling predefined `FieldPath`
  slots).
- Per-folder / per-tenant label variation.
- Changing terminology option semantics.
