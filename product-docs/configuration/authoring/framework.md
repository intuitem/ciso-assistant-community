---
description: A complete guide to authoring frameworks with the in-app builder, including the draft/publish lifecycle, translation workflow, and editorial discipline
---

# Framework authoring

A framework in CISO Assistant is a tree of **requirement nodes** that gets imported from a YAML library file. Authoring one well is more than translating a PDF into rows: the structure you pick drives how analysts navigate, how progress rolls up, and how the framework maps to others. This page is a complete walkthrough of the **in-app framework builder** — the recommended way to design a framework — followed by editorial discipline and a comparison with Excel-driven authoring.

You don't have to start from a blank page. A common pattern is to **fork an existing framework** — take a built-in one (or any community-shared library) as a baseline, then copy and tune it: rename the URN to your own namespace, prune the requirements you don't need, add organisation-specific ones, adjust the scoring scale, and ship it as a new library. This is the fastest route for industry-specific adaptations (an ISO 27001 variant for a regulated sector), internal policy frameworks that should align with NIST CSF, or regulatory frameworks that need extra in-house requirements layered on top. Forking keeps the editorial work focused on the _delta_ you actually care about, while inheriting the structure and conventions of a library that has already been battle-tested across audits.

## Framework builder

The platform ships with an **in-app framework builder** — a visual editor that lets you design a framework directly in the UI instead of (or alongside) the Excel + YAML round-trip. This is the **recommended authoring pattern going forward**: most of the structural decisions covered on this page can be expressed live in the builder, with real-time validation and a preview of how the framework will render to analysts.

You can reach it at **`/experimental/framework-builder`** in your instance. It's currently exposed under the _experimental_ namespace while the UX is being polished — the menu entry and URL are likely to move once it graduates, but the underlying tool is the same.

### Opening the builder

The landing page lists every framework on the instance plus a **New Framework** button:

- **Frameworks with Active Drafts** — pinned at the top, so you immediately see the in-progress work you can resume. Each row carries an _Editing_ badge and a **Continue Editing** button.
- **All Frameworks** — the full list, with status badges (_From Library_ vs _Custom_, optional _Editing_ badge if a draft is in progress, and a `v{n}` suffix for frameworks that have already been published once). _From Library_ means the framework came from a YAML library; _Custom_ means it was created on this instance.

Clicking **New Framework** creates an empty framework named _Untitled Framework_ in the root domain and jumps straight into the editor. Clicking **Edit** on an existing framework opens the editor too — the builder auto-creates an editing draft if one doesn't exist yet (`start-editing` is idempotent, so re-opening returns the same draft).

### The import guard — forking a library framework

Frameworks imported from a YAML library are not editable in place. Opening one in the builder shows a single screen with an amber lock icon, the message _"This framework was imported from a library"_, and a **Create copy and edit** button. The clone:

- Lands as a fresh framework in your root domain, named _"{original name} (copy)"_.
- Is fully editable — no import lock, no library backing.
- Gets its own URN, separate from the original library framework, so future library upgrades of the source don't touch your fork.
- Opens immediately in the editor with a blank draft seeded from the cloned content.

The original library framework stays intact and remains upgradable. This is the canonical fork-and-tune flow for adapting a published framework.

### The toolbar at a glance

A sticky **minimap** sits at the top of the editor and shows the framework's state at all times:

- A **back arrow** to the framework's detail page.
- A **status pill** describing where the draft sits relative to the live framework:
  - **Live** (green) — published; the draft matches what audit respondents see.
  - **Unpublished changes** (amber) — the draft differs from the live framework, but nothing is broken on live yet.
  - **Draft — nothing live yet** (amber) — the framework has draft content but has never been published; new audits will see nothing until you publish.
  - **Empty** (grey) — no content at all.
- **Preview** — opens the framework in a new tab, rendered as an analyst would see it (see [Preview](#preview) below). Greyed out when you have unsaved local edits; save first.
- **Export YAML** — downloads the current published state as a library-ready YAML file. If you have unpublished changes, a warning icon flags that the export reflects what's _live_, not your draft.
- **Language selector** — when the framework has target languages defined, this dropdown switches the editor into translation mode (see [Multi-language authoring](#multi-language-authoring)). A live progress counter (`translated/total`) tracks coverage.
- **Collapse / Expand all cards** — quickly fold the whole tree to scan the structure, or unfold to edit.
- **Keyboard help (`?`)** — opens the shortcut cheatsheet.
- **Save** — visible only when you have unsaved local edits. Persists the draft on the server.
- **Discard** — visible when the draft differs from live. Throws away the draft and re-creates a fresh one from the current live state.
- **Publish** — visible when the saved draft differs from live. Opens the publish preview modal before committing (see [Publishing](#publishing)).

A **table of contents** sits on the left, listing every section in the tree with active-section highlighting as you scroll. It can be collapsed to widen the editor.

### Adding nodes

Every node in the requirement tree is a **RequirementNode**. There's no separate "section" type at the data level — a node's role is determined by three properties:

- **`assessable`** — whether analysts answer this node (a leaf requirement) or it's purely a heading.
- **`display_mode`** — `default` for a normal node or `splash` for a presentational, non-assessable markdown block (see [Splash screens](#splash-screens)).
- Whether it has **children** — a non-assessable node with children is a section; an assessable node with children is rare but possible.

When you click **Add top-level node** (or the _Add child_ menu inside any node), a popover lets you pick a **preset**. The preset just seeds sensible defaults for `assessable` and `display_mode`:

| Preset | `assessable` | `display_mode` | Hint |
|---|---|---|---|
| **Blank** | false | default | Untyped — decide later (the safe default) |
| **Group** | false | default | A section header; will hold children |
| **Requirement** | true | default | A leaf the analyst will answer |
| **Splash screen** | false | splash | A presentational markdown block (intro, instructions, methodology notes) |

The choice is not binding — every field stays editable afterwards, including the `assessable` toggle (`⌘.` / `Ctrl+.`).

### The node card

Every node is rendered as a card with:

- A **drag handle** (grip icon) for reordering against its siblings — only the icon itself initiates the drag, so clicking elsewhere inside the card focuses fields normally.
- A **status line** at the top reporting the node's role at a glance: _Splash screen_, _Assessable requirement_, _Section with N children_, _Empty node_, etc.
- A **collapse chevron** (when there are children) to fold the subtree.
- A **ref_id** input (used for cross-framework mappings and as the human-readable code, e.g. `01.01`, `5.3.2`).
- A **name** input with a live character counter (200-char soft cap; turns red past 180).
- The **URN** in monospace — click to copy.
- A **description** textarea that auto-grows.
- An **Advanced** disclosure that hides three fields by default to keep the 80% case clean:
  - **Annotation** — auxiliary notes for the auditor / analyst.
  - **Typical evidence** — only shown for assessable nodes; describes what evidence would satisfy this requirement.
  - **Visibility expression** — a CEL expression (using the question values on this node) that hides the requirement when conditions aren't met. Authored via a [VisibilityEditor](../../concepts/audits.md#analyst-dimension-assignee--workflow-status) — same component used in audit field-visibility configuration.
- An **Implementation groups** chip selector (when IGs are defined on the framework).
- An **importance / weight** field for weighted scoring.
- The **Add child** menu and the **Add sibling** menu so you can grow the tree without leaving the keyboard.
- A **Delete** button with a confirmation prompt.
- Per-depth coloured left borders (blue / violet / amber / emerald cycling by depth) so nesting depth is visible at a glance — purple borders mark splash screens.
- A breadcrumb hint at depths ≥ 3 (_"Nested under {parent}"_) so you don't lose context when collapsed siblings make the immediate parent unclear.

The node card is keyboard-aware: focus inside it sets a hidden **focused-node** marker that the keyboard shortcuts (below) target.

### Keyboard shortcuts

Press **`?`** anywhere in the editor (outside an input) to open the cheatsheet. The shortcuts:

| Shortcut | Action |
|---|---|
| `Alt + →` | **Indent** the focused node (nest it as the last child of its previous sibling) |
| `Alt + ←` | **Outdent** the focused node (promote it to a sibling of its parent) |
| `Alt + Enter` | Add a **child** under the focused node |
| `Alt + Shift + Enter` | Add a **sibling below** the focused node |
| `⌘ + .` / `Ctrl + .` | Toggle **assessable** on the focused node — works even while typing |
| `⌘ + S` / `Ctrl + S` | Save draft |
| `?` | Show this cheatsheet |
| `Esc` | Close any open dialog |

The shortcuts use `e.code` rather than `e.key` so they stay reliable on macOS, where Option (`Alt`) can rewrite `e.key` for arrow keys and Enter.

### Splash screens

A **splash node** (`display_mode: splash`) is a presentational markdown block instead of a question. Use them for:

- A framework intro that opens the audit (the methodology, scope notes, regulatory citations).
- Inline instructions between sections.
- A closing summary that's part of the framework rather than a separate file.

Splash nodes render in the builder with a purple accent and a dedicated **Edit / Preview** toggle. The edit mode is a markdown textarea with formatting helpers:

- **Bold / Italic / Heading / Bullet list / Numbered list / Link / Table** — standard markdown buttons.
- **Insert image** — uploads via the `upload-image` endpoint, attaches to the framework, and inserts an `![image](…)` markdown link. The image is served back through `serve-image?attachment_id=…`, scoped to this framework.
- **Paste** — pasting an image from the clipboard uploads and inserts it inline automatically.

The preview pane renders the markdown the way an analyst will see it during the audit.

### Questions and choices

Any assessable node can carry one or more **questions** — the questionnaire layer that drives [flash mode](../../features/flash-mode.md), respondent flows, and scoring helpers. Click **Add question** inside the node to choose a type:

| Type | Stored as | Use |
|---|---|---|
| **Text** | `text` | Free-form answer |
| **Boolean** | `boolean` | Yes / No toggle |
| **Number** | `number` | Numeric input |
| **Number (slider)** | `number` with `config: {widget: 'slider', min, max, step}` | Bounded numeric input rendered as a slider |
| **Unique choice** | `unique_choice` | Radio buttons (one of N) |
| **Unique choice (slider)** | `unique_choice` with `config: {widget: 'slider'}` | The same choice list rendered as a slider over the choices in order |
| **Multiple choice** | `multiple_choice` | Checkboxes (any of N) |
| **Date** | `date` | Date picker |

Each question has a **ref_id** (auto-incrementing within the parent: `{node-refid}-q1`, `-q2`, …), an **order** within the node, optional **weight** for scoring, and a **dependency** (see below). Choice-typed questions get a **ChoiceListEditor** with:

- **Value** (the choice label).
- **ref_id** auto-generated as `{question-refid}-c1`, `-c2`, …
- **`add_score`** — points contributed to scoring when this choice is picked.
- **`compute_result`** — the compliance result this choice maps to (compliant / partially / non-compliant / not applicable / not assessed).
- **`select_implementation_groups`** — when this choice is picked, the framework can be auto-narrowed to specific IGs.
- **`color`**, **`description`**, **`annotation`** — presentation and reviewer notes.

Slider variants get a real-time validation hint on the question itself: min < max, step > 0, step ≤ range, ≥ 2 choices for `unique_choice:slider`. Errors surface inline while editing and re-validate at publish time.

#### Dependent questions (`depends_on`)

A question can be **shown only when** an earlier question on the same node has a specific answer. The **DependsOnEditor** picks:

- A **source question** — only questions earlier in the order are selectable, so you can't form cycles.
- A list of **answer choices** that trigger the dependency.

The collapsed question card shows a chip _"Shown when {ref} = {N answers}"_ so the conditional is visible without expanding the editor. This is how a framework can branch (_"If you answered No to Q1, skip Q2 and Q3"_) without manually duplicating requirements.

### Indent, outdent, drag, drop

The tree is fully malleable:

- **Drag and drop** — every node has a grip handle; drag to reorder against siblings. Drop targets re-index `order_id` automatically.
- **Indent / Outdent** — `Alt + →` nests a node as the last child of its previous sibling (only works if there _is_ a previous sibling); `Alt + ←` promotes a node up one level. Both operations recompute the depth of all descendants and rewrite `parent_urn` accordingly. Mouse equivalents exist via the node menu.

The tree's persistence shape is a flat array with `parent_urn` and `order_id` rather than nested children — this is intentional, so re-ordering doesn't trigger structural changes and the YAML format stays stable. The builder handles tree-vs-flat translation for you.

### Framework settings

A collapsible **Framework settings** panel sits between the header and the requirement tree, with a one-line summary (`{N} outcome rules, {M} implementation groups` or _"No rules or groups configured"_) when folded. Expanded, it carries:

#### Annotation

A free-form note attached to the framework — visible to analysts opening the framework's detail page. Used for editor notes, scope reminders, citations.

#### URN namespace and ref_id

These two fields determine the framework's identity in the URN scheme:

- **URN namespace** — the second segment of every URN the framework emits (`urn:{namespace}:risk:framework:{ref_id}`). Defaults to `custom`. Pick a stable namespace per organisation (e.g. `acme`) so all your forks share it and don't collide with library frameworks.
- **`ref_id`** — the framework's own short identifier, used in the URN's last segment and as the slug for child node URNs.

A live preview line shows the assembled URN (`urn:acme:risk:framework:my-framework`). Once any audit references this framework, **both fields lock** — the inputs go read-only with a tooltip explaining why, because changing URNs after audits exist would orphan every downstream link.

#### Scoring settings

A nested disclosure with three rows:

- **Min score** and **Max score** — the bounds of the scale (e.g. 0–100, 0–5, 1–3).
- **Aggregation** — how leaf scores roll up to the parent: **average** (the default) or **sum**.

Below them, a **Scale levels** editor for the actual scoring scale entries — each level has:

- **Score** (numeric).
- **Name** (e.g. _Initial_, _Managed_, _Defined_).
- **Description** (the criteria for reaching that level).
- Translations per language when in translation mode (side-by-side inputs for name and description).

This is the maturity scale your respondents will see when the audit is scored.

#### Outcome rules

The **OutcomesEditor** lets you author CEL expressions that compute outcome labels from the framework's score. Each rule carries:

- A **`ref_id`** (the label, e.g. `bronze`, `silver`, `gold`).
- An **expression** — a CEL boolean expression evaluated against the score and other framework variables.
- An **annotation** (description of what this outcome means).
- A **colour** for the outcome badge.

Multiple matching rules all apply, so you can stack tiers. Use the literal `true` as a catch-all (the inline hint reminds you). Rules are drag-orderable; the inline cheatsheet (toggle "Show CEL reference") lists the available operators and helper functions.

#### Implementation groups

Define the IG taxonomy: each entry carries `ref_id`, `name`, `description`, optional `default_selected` flag, and translations. These are the groups respondents will pick from at audit creation, and the labels they'll see in audit analytics' [Implementation Groups Breakdown](../../features/audit-analytics.md). See the [Implementation groups](../../concepts/audits.md#implementation-groups) concept for the two patterns (maturity tiers vs. scope slices).

Per-node IG assignment happens on the node card, not here — this section just defines the taxonomy.

#### Field visibility

A `VisibilityEditor` for the framework's default audit-field visibility — which fields auditees see, which are auditor-only, which are hidden. The same editor you'd use from the [audit field-visibility](../../guides/customize-audit.md) workflow, but pre-set here as the default for any audit spawned from this framework.

#### Languages

Two sub-sections:

- **Base language** — the framework's primary locale (defaults to English). Changing it triggers a **swap**: the current base content moves into `translations[oldLocale]` and the existing `translations[newLocale]` content (if any) is promoted to the base fields. This is destructive in the sense that the swap rewrites your storage layout — but it's reversible by swapping back.
- **Target languages** — locales for which you'll author translations. Adding a language doesn't write any content; it just exposes the language in the **Language selector** in the toolbar. Removing a target language deletes every translation stored for it.

The base+targets list propagates to `available_languages` on the framework, which is what audit creation reads to decide which language selector to show.

### Multi-language authoring

When at least one target language is defined, the toolbar's language selector becomes active. Switching to a target language puts the editor into **translation mode**:

- The **base content** stays visible on the left as a read-only reference (greyed out, in the base locale).
- A **translation input** sits on the right for every translatable field — name, description, annotation, typical evidence, splash markdown, question text, choice values and descriptions, IG names and descriptions, outcome annotations, score-scale names and descriptions.
- An **asterisk** (`*`) next to a label marks any base-content field that has no translation yet — the visual cue that something still needs work.
- A **progress counter** in the toolbar (`{translated}/{total}`) shows live coverage; it goes green at 100%.
- **Copy base** — a button that copies every untranslated base field into the active language as a starting point. Existing translations are preserved (never overwritten). This is the right starting move for a translation pass: copy base, then edit in place.
- The **add language** / **remove language** controls live in Framework Settings → Languages so they stay close to the rest of the metadata. Removing a target language drops all its translations on every node, question, choice, IG, outcome, and scale entry — confirm before clicking.

Translations are saved under the `translations` block of each object and ship inside the YAML library export under the same shape, so a framework authored multi-lingually round-trips cleanly.

### Preview

The **Preview** button (top toolbar) opens `/frameworks/{id}/builder/preview` in a new tab. It renders the framework the way a respondent will see it during an audit:

- A **navigation strip** down the side listing every assessable requirement and splash screen, with the splash screens shown distinctly.
- **Implementation group filters** — chips at the top let you toggle each IG on/off; only requirements tagged with the selected IG(s) (or with no IG at all) show through. Empty selection means _no filter_ (show everything).
- A **language switcher** — preview in any target language, exactly as a respondent would experience it.
- The **active requirement** is rendered with its full body: description, typical evidence (when assessable), splash markdown (when splash), and the **Question** component used live in audits, so you can fill in answers and verify the layout matches what you intended.

Preview is read-only against the draft — answers don't persist anywhere. It's a fidelity check, not a test audit.

The Preview link is disabled while you have unsaved local edits. Save first, then preview — that way the preview always reflects what's on the server, never a transient in-memory edit.

### The draft → publish lifecycle

The builder uses a server-side **editing draft** that's distinct from the live framework. The lifecycle is:

1. **Start editing** — on first open, the server creates an `editing_draft` JSON from the current live state. Re-opening returns the same draft (idempotent). Local edits update the draft in memory; the toolbar shows _Unsaved_.
2. **Save draft** — `⌘ + S` / `Ctrl + S` or the **Save** button serialises the in-memory state and PATCHes it onto the server. The status becomes _Unpublished changes_ (or _Draft — nothing live yet_ if the framework has never been published).
3. **Publish preview** — clicking **Publish** fetches a diff between the draft and live, opens a modal showing exactly what's about to change (see below). You can review and cancel without consequence.
4. **Publish** — confirms the preview. The server reconciles the draft into the relational tables (requirements, questions, choices) using URN matching: nodes that match an existing URN are updated in place, new URNs are added, missing URNs are removed. The framework's `editing_version` is incremented. The toolbar flashes _Published!_ and switches the status to _Live_.
5. **Discard** — at any time before publishing, the **Discard** button (with inline confirmation) deletes the draft on the server and re-creates a fresh one from live. This is the safe undo for "I want to start over from what's published."

#### Publish preview modal

Before committing, the modal shows the impact in four blocks:

- **Added** — requirements and questions present in the draft but not live. Each requirement is listed by name.
- **Removed** — requirements and questions present in live but not in the draft. Listed by name; same compliance assessments that referenced them will see those rows vanish.
- **Breaking changes** — fields whose change affects existing assessments (e.g. `assessable` flipped on an audited node, `ref_id` changed, scoring scale rewritten). Each entry shows the changed field, the object type, and its name.
- **Affected audits** — every existing compliance assessment that uses this framework, with explanatory hints if the publish adds or removes requirements (added requirements get spawned into existing audits; removed ones get pruned).

If the diff is empty (_No structural changes_), publishing is still possible — it'll bump the version with no functional difference, useful when you've only edited annotations or descriptions.

#### What if validation fails?

The **Publish** action runs `validateDraft` before committing:

- Framework name must be present and ≤ 200 chars.
- Per-node: name ≤ 200 chars, `ref_id` ≤ 100 chars, URN ≤ 255 chars.
- Per-question: slider variants need `min < max`, `step > 0`, `step ≤ range`; `unique_choice:slider` needs ≥ 2 choices.

Errors render inline against the offending node (with a `node-{id}` or `question-{id}` key) and block the publish. Fix them and re-publish; the publish flow auto-saves before re-running validation, so you don't lose the in-progress fix.

### Exporting to YAML

The **Export YAML** button in the toolbar downloads the current **published** state as a library-ready YAML file. The export uses the v2 library format and includes the full framework — meta, requirement tree, questions, choices, IGs, outcomes, scoring scale, translations. The resulting file is what you'd ship to:

- A community library catalogue.
- Another CISO Assistant instance.
- Source control as a versioned artefact.

If you have unpublished draft changes, a warning icon flags that the export reflects what's live, not your draft — publish first if you want the draft included.

### What the builder doesn't do (yet)

A few authoring tasks still require the YAML / Excel path:

- **Bulk imports from a spreadsheet** — the builder edits one framework at a time. Bringing in a published standard from an Excel source is still best done through `convert_library_v2.py` and then loading the YAML.
- **Mappings to other frameworks** — defined in their own library files and not authored from within a framework. See the [Mappings concept](../../concepts/mappings.md).
- **Reference controls and threats** — bundled in the same library as a framework when shipped, but authored elsewhere on the platform.
- **Cross-framework refactors** — renaming a shared IG ref across multiple frameworks is a one-by-one operation in the builder.

For these, fall back to [Designing your own libraries](../libraries/custom-libraries.md) or [Excel-driven authoring](excel.md).

### When to use the builder vs. Excel

- **Builder** — for frameworks that live primarily on this instance (internal policies, forked variants, in-progress drafts), and for any iterative editing where the round-trip cost of Excel-to-YAML conversion is too high. The builder also wins anywhere a translation pass matters — the side-by-side editing and progress counter are hard to replicate in spreadsheets.
- **Excel** — for frameworks you intend to ship as a library file (community catalogue, multi-instance deployments, version-controlled releases), and for the initial conversion of a published standard from its source spreadsheet. See [Excel-driven authoring](excel.md) and [Designing your own libraries](../libraries/custom-libraries.md).

The two paths are not mutually exclusive: a framework you built in Excel can be loaded as a library, forked through the builder, and tuned in place; conversely, a framework drafted in the builder can be exported to YAML for redistribution.

## Editorial discipline

The builder will let you do almost anything, but the choices that age well are narrower. A few principles worth holding to:

### Requirement tree shape

- **Prefer breadth over depth.** A framework that's 3 levels deep with 10 leaves at each section reads cleanly; a 6-level tree with 1–2 leaves per branch is exhausting. Two levels is enough for most standards; three is the realistic limit before navigation starts hurting.
- **Sections vs requirements is a single toggle.** Don't pre-design a separate "section type" mental model — every node is just `(assessable, display_mode)`. Use sections for navigation, requirements for assessment, splash screens for prose.
- **Don't over-nest.** If a section has only one assessable child, the section is probably noise. Flatten.

### Naming and IDs

- **Stable `ref_id`s outlive renames.** The `ref_id` is what appears in mappings, audit exports, and analyst conversations ("we're failing 5.3.2"). Pick a scheme that survives reorganisation: typically `{section}.{subsection}.{leaf}` with zero-padding (`05.03.02` sorts; `5.3.2` doesn't, past 9).
- **URN namespace identifies the publisher, not the framework.** Use one namespace per organisation (`acme`, not `acme-iso27001-v2`). The framework's `ref_id` differentiates frameworks within that namespace.
- **Lock the URN before publishing widely.** Once audits exist, the URN namespace and `ref_id` lock in the builder anyway — but renaming before that point still ripples into every external mapping that pointed at the old URN.

### Implementation groups

- **Add IGs only when there are two recognised tiers.** A framework with a single IG isn't using the feature; it's adding navigation overhead.
- **Maturity tiers should be cumulative.** IG1 ⊂ IG2 ⊂ IG3 is the natural pattern (CIS, FedRAMP). Non-cumulative IGs (scope slices like _Cloud_ vs _On-prem_) are valid but rarer — say so in the IG description.
- **Default-selected IGs save respondent friction.** If most audits will pick IG1, set `default_selected: true` on it; the audit creation form pre-selects it.

See [Implementation groups](../../concepts/audits.md#implementation-groups) for the two recurring patterns.

### Scoring scales

- **Match the standard the framework comes from.** CMMI uses 0–5; NIST CSF 2.0 uses 1–4; ISO 27001 has no inherent scale. Don't reinvent unless the standard genuinely lacks one.
- **Document each level.** The scale-entry description is what an analyst reads to decide whether they're at level 3 vs level 4 — make it actionable, not just a label.
- **Documentation score is opt-in per audit.** The framework declares the scale; the audit decides whether to ask for two scores (implementation + documentation) or one (maturity).

### Questions

- **Use questions where the requirement isn't actionable on its own.** If a requirement says "Define and maintain an asset inventory," the question layer can ask "How frequently is the inventory reviewed?" — converting prose into a structured signal.
- **Scoring questions over scoring requirements.** When you want flash-mode-style scoring, drive it from `add_score` on question choices, not from manual per-requirement scoring. The question layer is the structured-input layer.
- **Watch the dependency graph.** Conditional questions (`depends_on`) are powerful but expensive to debug. Keep them shallow (a single hop, not chains).

### Reference controls and threats

These ship in the same library YAML as a framework when distributed, but they live in their own catalogues on the platform. Bundle them when:

- The framework prescribes specific controls (e.g. CIS Controls v8 has its own control catalogue).
- The framework references named threats that don't exist in the platform's built-in threat list.

When in doubt, ship them separately — a framework that depends on a separately-loaded control catalogue stays leaner and lets users mix-and-match.

### Mappings

- **Author mappings as a separate library**, not inside a framework. The [Mappings concept](../../concepts/mappings.md) page explains the data model. A single mapping library can reference URNs from two frameworks shipped independently.
- **Map at the leaf level**, not at the section level. Section-to-section mappings rarely survive small reorganisations of either side.

### Localisation

- **Author in the base language first.** Trying to write in two languages simultaneously means neither version is canonical. Finish English (or whatever your base is), then translation-pass with Copy base + edit.
- **Don't translate ref_ids or URNs.** They're identifiers, not user-facing text. The translations dict only covers `name`, `description`, `annotation`, `typical_evidence`, question `text`, choice `value` / `description`.

## Existing material

- [Designing your own libraries](../libraries/custom-libraries.md) — full Excel-to-YAML reference, including the framework schema.
- [Getting your custom framework](../libraries/custom-frameworks.md) — quick-start for a single-framework library.
- [Frameworks concept](../../concepts/frameworks.md) — what a framework _is_ in the data model.
- [Multi-level support](../../features/multi-level-support.md) — how implementation groups are selected at audit creation.

## Related

- [Risk matrix authoring](matrix.md) — the other half of most security libraries.
- [Excel-driven authoring](excel.md) — when to fall back to spreadsheets.
- [Library upgrade](../libraries/library-upgrade.md) — what changes are safe to ship in a v1.1 of a framework you've authored.
- [Contributing → Frameworks and libraries](../../contributing/framework.md) — how to upstream a framework to the community catalogue.
