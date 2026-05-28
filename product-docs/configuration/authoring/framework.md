---
description: Task-oriented recipes for authoring a framework — fork, build a tree, score, translate, publish
---

# Framework authoring

A framework in CISO Assistant is a tree of **requirement nodes** that gets imported from a YAML library file. The recommended way to author one is the **in-app framework builder**, which lives at **`/experimental/framework-builder`**. This page is a set of task-oriented recipes — find the one that matches what you're trying to do, follow the steps. For the complete walkthrough of every surface in the editor, see [Framework builder — reference](framework-builder.md).

{% hint style="warning" %}
**Experimental.** The framework builder is exposed under the `/experimental/` namespace while its UX is being polished. The URL and menu entry are likely to move once it graduates, and individual surfaces may change between releases. The underlying data stays — your drafts and published frameworks aren't at risk — but expect occasional rough edges. Feedback is welcome.
{% endhint %}

You don't have to start from a blank page. A common pattern is to **fork an existing framework** — take a built-in one (or any community-shared library) as a baseline, then copy and tune it: rename the URN to your own namespace, prune the requirements you don't need, add organisation-specific ones, adjust the scoring scale, and ship it as a new library. This is the fastest route for industry-specific adaptations (an ISO 27001 variant for a regulated sector), internal policy frameworks that should align with NIST CSF, or regulatory frameworks that need extra in-house requirements layered on top.

## Tasks

### Create a brand-new framework

1. Go to **`/experimental/framework-builder`**.
2. Click **New Framework**. A framework named _Untitled Framework_ is created in your root domain and the editor opens.
3. Type the framework name in the title field at the top and an optional description below.
4. Open **Framework settings** (the collapsible panel under the title) and set the **URN namespace** (e.g. `acme`) and **ref_id** (e.g. `my-policy`). The assembled URN previews live below the inputs.
5. Click **Add top-level node** at the bottom and choose a preset (**Group** for a section header, **Requirement** for a leaf the analyst will answer).
6. Save with `⌘ + S` / `Ctrl + S` whenever you've made progress — the status pill flips to _Draft — nothing live yet_ until you publish.

> See: [Framework settings](framework-builder.md#framework-settings), [Adding nodes](framework-builder.md#adding-nodes) in the reference.

### Fork an existing framework

When you want to start from a built-in or community framework rather than from scratch:

1. Open **`/experimental/framework-builder`**.
2. Click **Edit** on the framework you want to fork (it'll be marked _From Library_).
3. You'll see an amber lock screen — _"This framework was imported from a library"_. Click **Create copy and edit**.
4. A fully editable copy named _"{original name} (copy)"_ opens. The original library framework stays untouched and remains upgradable.
5. Open **Framework settings** and rename the **URN namespace** to your organisation (replace the source's namespace; otherwise your fork looks like an upstream variant). Update **ref_id** if you want a different short identifier.
6. Prune, add, or rename nodes as needed. Save and publish when ready.

> Important: do this **before any audit references the fork**. Once an audit exists, the URN namespace and ref_id lock automatically and can't be changed.

### Build the requirement tree

1. Click **Add top-level node** at the bottom of the editor to add a root-level node, or the **Add child** menu inside an existing node to nest.
2. Pick a preset:
   - **Group** for a section header (won't be assessed).
   - **Requirement** for a leaf the analyst will answer.
   - **Splash screen** for a presentational markdown block (intro, methodology).
3. Fill in the **ref_id** (e.g. `5.3.2`) and **name**. The character counter on the name field warns past 180 chars (200-char limit).
4. Use keyboard shortcuts to grow the tree without leaving the keyboard:
   - `Alt + →` — indent the focused node (nest as last child of previous sibling).
   - `Alt + ←` — outdent (promote one level up).
   - `Alt + Enter` — add a child.
   - `Alt + Shift + Enter` — add a sibling below.
   - `⌘ + .` / `Ctrl + .` — toggle assessable.
5. Drag the grip handle (left of any node) to reorder against siblings.

> See: [Keyboard shortcuts](framework-builder.md#keyboard-shortcuts), [Indent, outdent, drag, drop](framework-builder.md#indent-outdent-drag-drop) in the reference.

### Add implementation groups (IGs)

When the framework should support tiered selection (e.g. _Basic_ / _Standard_ / _Advanced_):

1. Open **Framework settings** → expand **Implementation groups**.
2. Click **Add group**. For each group set:
   - **`ref_id`** — a short identifier (e.g. `IG1`).
   - **Name** — what users see at audit creation (_"Basic"_).
   - **Description** — when this IG applies.
   - **Default selected** — tick if most audits should pre-select this IG.
3. On each requirement node, click the **Implementation groups** chip selector and tick the IGs that include this requirement. Empty selection means _every IG_ includes it.
4. Use the **Preview** button (top toolbar) and the IG filter chips to verify which requirements show up under each IG.

> See: [Implementation groups](../../concepts/audits.md#implementation-groups) for the conceptual context.

### Add a scoring scale

1. Open **Framework settings** → expand **Scoring settings**.
2. Set **Min score** and **Max score** to the scale bounds (e.g. 0–5 for CMMI-style, 0–100 for percentage).
3. Choose **Aggregation**: _Average_ (default — leaf scores average up to the parent) or _Sum_.
4. Expand **Scale levels** and click **Add scale level** for each maturity level. Per level:
   - **Score** (numeric).
   - **Name** (e.g. _Initial_, _Managed_, _Defined_).
   - **Description** (criteria for reaching this level).
5. Repeat for each level. The platform uses these definitions to render the scale in audits.

### Override scoring on a requirement

Use a requirement-level override when one requirement has a different valid range from the rest of the framework, for example a binary `0..1` requirement inside a `0..5` maturity framework.

In YAML or Excel, set these fields on the requirement node:

- **`min_score`** — the requirement's minimum score.
- **`max_score`** — the requirement's maximum score.
- **`scores_definition`** — optional level labels for that requirement's effective range.

The fields cascade independently. You can override only `max_score`, only the labels, or the full range. If the requirement changes range but does not define its own labels, the framework-level labels are reused only when they cover the requirement's effective range; otherwise the audit shows the numeric scale without mismatched labels.

Keep question scoring aligned with the effective range: any `add_score` values on choices should fit between the requirement's effective `min_score` and `max_score`.

### Add a yes/no question to a requirement

1. On the requirement node card, click **Add question** at the bottom.
2. Pick **Boolean** from the type picker.
3. Type the question text in the question card (e.g. _"Is the policy reviewed annually?"_).
4. Optional: open the question's Advanced disclosure to set a **weight** (for scoring) or a **depends_on** rule (show only when a previous question on this node has specific answers).

> See: [Questions and choices](framework-builder.md#questions-and-choices) in the reference for the full type list.

### Add a multi-choice scoring question

For flash-mode-style scoring where each choice contributes points:

1. On the requirement node, click **Add question** → **Unique choice**.
2. Type the question text (e.g. _"How mature is your access review process?"_).
3. Below the question, click **Add choice** for each option. Per choice:
   - **Value** — the label (e.g. _"Annual review documented"_).
   - **`add_score`** — points contributed when this choice is picked.
   - **`compute_result`** — optionally map the choice to a compliance result (_compliant_ / _partially compliant_ / etc.).
   - **`color`** — optional, for visual differentiation.
4. Repeat for each choice. The order in the editor is the order respondents see.

### Add bronze/silver/gold outcomes

To assign labels based on the final score (e.g. _Bronze_ if 60+, _Silver_ if 80+, _Gold_ if 95+):

1. Open **Framework settings** → expand **Outcome rules**.
2. Click **Add rule**. For each tier:
   - **`ref_id`** — the label (e.g. `bronze`).
   - **Expression** — a CEL boolean expression (e.g. `score >= 60`).
   - **Annotation** — what reaching this tier means.
   - **Colour** — for the outcome badge.
3. Multiple matching rules all apply, so add tiers in any order. Use the literal `true` as a catch-all if you want a default tier.
4. Toggle **Show CEL reference** if you need a refresher on the operators and helper functions.

### Translate to another language

1. Open **Framework settings** → **Languages** → in the **Target languages** dropdown, pick the language you want to add (e.g. _French_). Click **Add**.
2. Save the draft.
3. Open the **Language selector** in the toolbar and switch to the language you just added. The editor switches to translation mode — every field becomes a base-vs-translation pair.
4. Click **Copy base** in the toolbar to seed every untranslated field with the base content as a starting point (existing translations are preserved).
5. Walk through every node, question, choice, IG, outcome, and scale entry. The asterisk (`*`) next to a label flags fields that still have no translation; the toolbar's `translated/total` counter shows live coverage.
6. Save when done. The progress counter turns green at 100%.

> See: [Multi-language authoring](framework-builder.md#multi-language-authoring) in the reference.

### Preview before publishing

1. Save your draft (`⌘ + S`). The **Preview** button greys out while you have unsaved local edits.
2. Click **Preview** in the toolbar — opens `/frameworks/{id}/builder/preview` in a new tab.
3. Use the IG chips at the top to test how the framework will scope to each IG selection.
4. Use the language switcher to preview in any target language.
5. Click through every requirement on the side strip — answer the questions if you want to verify the layout. Answers don't persist; preview is read-only.

### Publish your draft

1. Save your draft. The **Publish** button only becomes active when the saved draft differs from live.
2. Click **Publish**. A modal opens with a diff:
   - **Added** — new requirements, questions, choices.
   - **Removed** — items present in live but not the draft.
   - **Breaking changes** — fields whose change affects existing audits.
   - **Affected audits** — every audit that uses this framework, with hints about added/removed requirements.
3. Review the diff carefully. Cancel if anything looks wrong; the draft stays untouched.
4. Click **Confirm publish**. The toolbar flashes _Published!_ and the status pill turns _Live_.
5. If validation fails (e.g. slider min ≥ max, name too long), errors render inline on the offending node. Fix them and re-publish.

> See: [Publish preview modal](framework-builder.md#publish-preview-modal) in the reference.

### Discard a draft

When you want to throw away in-progress edits and start over from the live state:

1. In the toolbar, click **Discard**. An inline _"Discard all changes?"_ prompt appears.
2. Click **Yes, discard**. The server-side draft is deleted and a fresh one is created from the current live state.
3. The editor reloads with the live content.

### Export as a YAML library

To take a framework out of this instance — for source control, sharing with another instance, or shipping to the community catalogue:

1. Make sure you've published any draft changes you want included (the export reflects what's _live_, not the draft).
2. In the toolbar, click **Export YAML**. The browser downloads a library-format YAML file with the full framework: metadata, requirement tree, questions, choices, IGs, outcomes, scoring scale, translations.
3. The file is ready to load on another instance through the [Libraries](../libraries/README.md) section, or to commit to source control.

> Warning: if you have unpublished draft changes, the export button shows a warning icon — the YAML reflects the live state, not your in-progress draft.

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
- **Use requirement-level overrides sparingly.** They are designed for genuinely mixed scoring models. If every requirement needs the same range, keep it at framework level so audits and outcomes stay easier to reason about.
- **Check aggregation semantics.** Average-based methods normalise mixed ranges before roll-up; sum-based scoring adds raw weighted values, so a `0..1` requirement contributes much less than a `0..100` requirement unless its weight compensates for that.

### Questions

- **Use questions where the requirement isn't actionable on its own.** If a requirement says _"Define and maintain an asset inventory,"_ the question layer can ask _"How frequently is the inventory reviewed?"_ — converting prose into a structured signal.
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

## When to use the builder vs. Excel

- **Builder** — for frameworks that live primarily on this instance (internal policies, forked variants, in-progress drafts), and for any iterative editing where the round-trip cost of Excel-to-YAML conversion is too high. The builder also wins anywhere a translation pass matters — the side-by-side editing and progress counter are hard to replicate in spreadsheets.
- **Excel** — for frameworks you intend to ship as a library file (community catalogue, multi-instance deployments, version-controlled releases), and for the initial conversion of a published standard from its source spreadsheet. See [Excel-driven authoring](excel.md) and [Designing your own libraries](../libraries/custom-libraries.md).

The two paths are not mutually exclusive: a framework you built in Excel can be loaded as a library, forked through the builder, and tuned in place; conversely, a framework drafted in the builder can be exported to YAML for redistribution.

## Related

- [Framework builder — reference](framework-builder.md) — every surface and action in the builder.
- [Risk matrix authoring](matrix.md) — the other half of most security libraries.
- [Excel-driven authoring](excel.md) — when to fall back to spreadsheets.
- [Designing your own libraries](../libraries/custom-libraries.md) — the full Excel-to-YAML reference.
- [Getting your custom framework](../libraries/custom-frameworks.md) — quick-start for a single-framework library.
- [Frameworks concept](../../concepts/frameworks.md) — what a framework _is_ in the data model.
- [Library upgrade](../libraries/library-upgrade.md) — what changes are safe to ship in a v1.1 of a framework you've authored.
- [Contributing → Frameworks and libraries](../../contributing/framework.md) — how to upstream a framework to the community catalogue.
