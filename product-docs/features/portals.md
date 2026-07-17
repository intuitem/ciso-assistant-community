---
description: Configurable launcher surfaces — internal tile dashboards and public, read-only trust centers
---

# Portals and trust center

{% hint style="info" %}
**Feature flag.** Portals are off by default. An administrator enables them under **Settings → Feature flags → `custom_portals`**. With the flag off, the menu entry is hidden and the whole API (authoring and public) is unreachable. Available on both the community and enterprise editions.
{% endhint %}

A **portal** is a configurable grid of tiles you compose yourself. Two flavours share the same editor:

- **Internal portals** — an authenticated launcher (behind login) that points users at the objects, pages, and questionnaires you want them to reach.
- **Public portals (trust centers)** — a read-only, unauthenticated page reachable by anyone with the link, surfacing your compliance posture, certifications, and published documents.

## For users

### Where it lives

- **Authoring:** sidebar → **Manage portals** (`/portal-editor`), or the **Portals** button in the top app bar.
- **Internal viewer:** `/portal` (the launcher) and `/portal/<id>` (a specific portal).
- **Public trust center:** `/trust/<link-token>`, plus the short `/trust` vanity URL for the one you mark as primary.

### When to use it

- Give a team or audience a curated home screen instead of the full app — _"here are the three things you do here."_
- Publish a customer-facing **trust center** so prospects and auditors can self-serve your certifications and live compliance status without an account or a back-and-forth email thread.

### Building an internal portal

1. On **Manage portals**, under **Internal portals**, select **Add** → **New internal portal**. This opens the editor.
2. Name the portal in the title field (it auto-saves on blur).
3. A portal is a list of **groups**, each holding **tiles**. Use **Add group** and **Add item** to build the grid.
4. Each tile has an **Icon**, a **Title**, a **Kind**, and a kind-specific target. Internal portals offer these kinds:
   - **Create** — a button that opens the create form for a model (e.g. incidents, applied controls).
   - **Navigate** — link to a model's list page or a built-in page.
   - **Questionnaire** — launch an audit from a framework you pick (see below).
   - **External** — open an external `https://` link in a new tab.
5. Use the segmented **Edit / Preview / Settings** control at the top to preview the grid or open settings, then **Save**. Toggle availability with **Publish** / **Unpublish**.

{% hint style="info" %}
**Questionnaire tiles** create a real audit when clicked. The framework, domain, and mode come from the tile configuration, not the clicker — so a user can only create what you wired up. You can fix the domain, or leave it to the clicker (including their personal **My space**), let them name the audit (**Let the user name it**), pick implementation groups, set answering visibility, and choose a full audit or a self-service respondent run.
{% endhint %}

### Building a public portal (trust center)

1. Under **Public portals**, select **Add** → **New public portal**, or open any portal's **Settings** and turn on **Make this portal public**.
2. Public portals offer only public-safe tile kinds: **Certification / Document**, **Framework**, and **External**.
   - **Certification / Document** — a badge built from a FontAwesome icon + your label, with optional validity dates, linking to an external URL or an uploaded document.
   - **Framework** — surfaces a **framework snapshot** as a compliance donut that drills down into the requirement tree (see below).
3. In **Settings → Trust center**, set the **Tagline**, **Logo URL**, and **Accent color** for branding. Mark one portal as the **Primary trust center** to claim the short `/trust` URL (this requires administrator rights).
4. The **Public link** panel shows the shareable URL; **Regenerate link** revokes the old one instantly.

{% hint style="warning" %}
A public portal is only served while it is **published and enabled**. Unpublishing it (or disabling it) takes the trust center — and the snapshots and documents it surfaces — offline immediately, even for someone who already has the link.
{% endhint %}

### Framework snapshots

A **framework snapshot** is a frozen, audit-derived view of a framework's compliance posture. Manage them from the **Public portals** section → **Framework snapshots** (`/portal-editor/snapshots`).

- Create one by picking a **domain**, then one of its **audits**, then the **implementation groups** to mirror (leave empty to mirror all).
- Each snapshot captures the result breakdown, score, the per-requirement tree, and the controls touched — and only changes when you **re-sync**. Use **Review changes** to preview the diff before **Apply sync**.
- Choose what the public donut shows: **Score and result**, **Score only**, or **Result only**.
- On the trust center, a framework tile renders the donut; clicking it opens a drill-down with the collapsible requirement tree and CSV / Excel export.

### Public documents

Files published to your trust center — certifications, reports, policies. Manage them under **Public documents** (`/portal-editor/documents`). Each is stored in an **isolated public URL, separate from internal evidence**, and is served from your own origin (no external image or document hotlinking required). A document is only reachable while a published public portal references it.

### Landing on a portal

Set **default landing** to a portal so users arrive on `/portal` instead of analytics — configurable per-user (profile preference) or as the organisation default in general settings.

## For implementers

- **Surface area.** Django app `backend/portals/` — models `Portal`, `PortalPreset`, `FrameworkSnapshot`, `PublicDocument` (a portal's groups/tiles live in `Portal.content` JSON, not separate models). Routers and public views are mounted at the API root via `portals/urls.py`. Frontend: authoring under `routes/(app)/(internal)/portal-editor/`, the authenticated viewer under `routes/(portal)/portal/`, and the public trust center under `routes/trust/`; components in `lib/components/PortalEditor/`, `PortalGrid/`, and `TrustPortal/`.
- **API.** Authenticated, flag-gated, IAM-scoped: `/api/portals/`, `/api/portal-presets/`, `/api/framework-snapshots/`, `/api/public-documents/`. Unauthenticated, token-gated: `/api/public/portals/<token>/`, `/api/public/portals/primary/`, `/api/public/snapshots/<token>/` (+ `/export/`), `/api/public/documents/<token>/`.
- **Key integration points.** Snapshots derive from `ComplianceAssessment` and its `RequirementAssessment` results. Questionnaire tiles create a `ComplianceAssessment` (and, in respondent mode, a `RequirementAssignment`). Personal **My space** folders are provisioned just-in-time via the `personal_folders` setting.
- **Gotchas.**
  - Public portal serving requires `is_public=True`, `enabled=True`, and `status=PUBLISHED` together.
  - Snapshot and document tokens are only served while a published public portal still references them (reachability gate), so unpublishing revokes public access even if a token leaked.
  - Marking a portal **Primary trust center** (`is_primary`) is an instance-wide effect and requires `change_globalsettings` on the root folder, not just folder-scoped `change_portal`.
  - `branding.accent_color` / `logo_url` are validated server-side and re-guarded client-side, since they render on an anonymous page.
- **Configuration.** Feature flag `custom_portals` (default off) gates the whole feature — viewsets append `FeatureFlagRequired`, and the public views are gated by it too.

## Status

- **Owner:** intuitem
- **Feature flag:** `custom_portals` — default **off**
- **Edition:** community and enterprise

## Related

- [Audits](../concepts/audits.md) — the source of framework snapshots
- [Domains](../concepts/domains.md) and [IAM and scoping](../concepts/iam-and-scoping.md) — audience and folder scoping
- [Feature flags](../configuration/settings/feature-flags.md) — enabling `custom_portals`
- [Assignments / respondent mode](assignments.md) — how questionnaire tiles provision self-service runs
