# The library builder mints URNs from ref_ids, numbers default ids after the highest one, and caps the packager at 32 characters

- Status: Proposed
- Date: 2026-10-08
- Deciders: @martinzerty

## Context

A URN is the identity of every library object: requirements, questions and choices included. Publishing updates objects by URN, audit answers are attached to them, mappings and CEL rules refer to them. Every URN column is limited to 255 characters in the database (Postgres rejects longer values, SQLite stores them).

In the library builder, a new question's default ref_id was `<requirement ref_id>-q<n>`, and a question URN is `<requirement URN>:question:<ref_id>`, so the requirement's ref_id appeared twice in every default question URN. With long ref_ids, question and choice URNs went over 255 characters (CA-1854). Validate reported it only after the URNs were saved, and saved URNs are frozen and read-only in the editor, so the author could not fix them.

Several places mint URNs, with different rules (Annex A). Shipped libraries are far from the limit: their longest URN is 172 characters and their longest packager 18 (Annex B). The overflow comes from content authored in the builder.

This ADR covers the URNs built by the library builder: the framework and quick form editors, framework and quick form creation in a draft, adding objects to a draft, renaming a draft, importing objects, and adopting a live framework (`library/live.py`). The Excel converter, the `tools/excel` scripts and the workflow export are out of scope: they keep their own rules (Annex A), and nothing they ship comes close to the limit. The frontend's temporary URNs are never stored and are not covered either.

## Decision

We will keep one minting rule for every builder path: segments come from ref_ids cleaned by `urn_safe_leaf`, default ids take the highest number already used plus one (except when adopting a live framework, see below), and only the packager gets a new length cap (32 characters). We do not guarantee URN length at save time, and we never rewrite the end of an existing URN: only renaming an unpublished draft changes its start.

This scheme deliberately binds the builder paths only, not every URN producer: the Excel converter, the `tools/excel` scripts and the workflow export keep their own rules (Annex A). Their shipped content stays far below the limit (Annex B), and aligning the converter would affect the compatibility modes it keeps for existing files; that is a separate decision (see Alternatives).

### Scheme

```
library      urn:{packager}:risk:library:{library}
object       urn:{packager}:risk:{type}:{library}[:{object}]
requirement  urn:{packager}:risk:req_node:{library}:{requirement}     (quick form page: qf_page)
question     {requirement URN}:question:{question}
choice       {question URN}:choice:{n}
```

The object segment is omitted for the only object of its kind in the library (framework, quick form, risk matrix).

| Segment | Comes from | Max length |
|---|---|---|
| `packager` | the draft's packager, `[a-z0-9_-]` | 32 characters (new) |
| `type` | the canonical token (`framework`, `req_node`, `threat`, `reference_control`, …). Legacy spellings (`function`, `reference-controls`) are read, never minted | 17 characters (`reference_control`), fixed tokens |
| `library` | the draft's ref_id, `[a-z0-9_-]` | 100 characters (unchanged) |
| `object` | the object's ref_id, cleaned | 100 characters, plus `-N` when an import renames it on collision (unchanged) |
| `requirement` | the requirement's ref_id, cleaned; `node{N}` when it has none | 100 characters, plus `-N` on collision (unchanged). Imported and legacy ids may span several `:`-separated segments; they are kept as is, with no cap |
| `question` | the question's ref_id, cleaned: the editor's default is a number, an author may type a name (`headcount`) | 100 characters (the ref_id column), plus `-N` on collision (unchanged) |
| `choice` | a number | a number; `live.py` may add `-N` on collision |

These caps do not add up to 255: the total can still exceed the limit (see Length).

Cleaning is `urn_safe_leaf`: surrounding whitespace is dropped, the value is lowercased, each run of characters outside `[0-9a-z[]()._-]` becomes a single `-`, and leading and trailing `-` are trimmed (`A  1/Access` gives `a-1-access`). A segment never contains `:`.

### Default ids and collisions

- A default id takes the **highest number already used + 1**, never the first free one:
  - `node{N}` for a requirement without ref_id, counted over the framework (editor and `live.py`);
  - the editor's default question ref_id, counted over the requirement's questions. Only plain numbers (`3`) and legacy ids (`2.1-q3`, `q3`) count, named questions never do;
  - a question reaching the backend without ref_id;
  - a choice: `:choice:{n}`.
- A deleted id therefore comes back only when it was the highest one.
- When a generated id is already taken, it gets a `-2`, `-3`, … suffix. Every path uses this same form, but the check is implemented separately: the editor (`framework_editor.py`) and the draft paths (`builder.py`) look for taken ids in the draft, `live.py` among the sibling rows already in the database. When an author creates an object whose ref_id is already used in the draft, it is refused (`objectUrnAlreadyExists`, HTTP 409).
- Exception to the highest-number rule: `live.py` fills the question and choice URNs missing on a live framework by position (`:question:{position}`, `:choice:{position}`), as before. It only completes rows that already exist, in their stored order.

### Length

The builder does not check URN length at save time. URNs over 255 characters are reported by Validate and refused at publish (`_check_field_lengths`), as today. Removing the repeated ref_id makes this rare; it remains possible with very long ref_ids (a library and a requirement ref_id of 100 characters each), a long typed question name, or a rename to a longer ref_id.

### Packager

The packager is the URN namespace. RFC 8141 limits a URN namespace identifier (NID) to 32 characters, and only that length is borrowed: the packager alphabet stays `[a-z0-9_-]`, which also allows `_` and a leading or trailing `-`, unlike an RFC NID.

The cap applies to every new or changed identity: draft creation and update, the `default_packager` setting, and the frontend inputs, including prefilled values. A YAML import whose packager is longer is refused. Adopting a stored library or a live framework keeps its identity unchanged. A value predating the cap keeps saving while it is resubmitted unchanged, both on a draft and in the setting.

A `default_packager` longer than 32 characters is still prefilled in both create forms (framework and quick form): the form flags it (`lbListPackagerPattern`) and keeps the create button disabled until the author types a packager of at most 32 characters. Drafts can still be created; they just can't take the old default as is.

The Excel converter and the `tools/excel` scripts take the packager from the library's metadata and do not cap it; the longest shipped packager is 18 characters (Annex B).

### Existing URNs

- The end of a URN already published, stored or saved in a draft is never rewritten, even when it doesn't follow the scheme: nested `:` in requirement ids, segments longer than 32 characters, legacy type tokens, legacy library URNs, named questions. The only changes are the start rewritten when an unpublished draft is renamed (below), and the lowercasing `live.py` applies to the URNs of a live framework it adopts.
- Drafts that already hold URNs over 255 characters keep them; Validate and publish keep reporting them. Workarounds: recreate the question (it gets a short number), or export the YAML, shorten the URNs and import it as a new draft.
- Renaming an unpublished draft rewrites the start of every URN and keeps the rest, so the CEL keys of a draft with a single framework do not change. In a legacy draft holding several frameworks, each framework's segment is re-derived from its ref_id, so its requirements' keys change when that ref_id differs from the old segment (`fw-a:1` becomes `fw-a-v2:1`).
- Questions with a legacy default ref_id (`a.1-q1`) keep their URN; new questions on the same requirement get the next number.

### CEL keys

The key of an item in a CEL rule is **everything after the 5th `:` of its stored URN**, as stored (`extract_node_id`).

| Item | URN | CEL |
|---|---|---|
| requirement | `urn:acme:risk:req_node:lib:5.3.2` | `requirements["5.3.2"]` |
| question | `…:5.3.2:question:1` | `answers["5.3.2:question:1"]` |
| named question | `…:5.3.2:question:headcount` | `answers["5.3.2:question:headcount"]` |
| choice | `…:5.3.2:question:1:choice:2` | `"5.3.2:question:1:choice:2" in answers["5.3.2:question:1"].selected_choices` |
| quick form page | `urn:acme:risk:qf_page:lib:page-1` | `pages["page-1"]` |

The requirement part is the requirement's ref_id cleaned by `urn_safe_leaf` when it was first saved (`A 1/Access` gives `a-1-access`), `node{N}` without ref_id, or a `-2` suffixed id on collision. Once the item has been saved and the editor reloaded, it no longer changes when the ref_id is edited. Imported and legacy requirements may span several segments (`1:3`).

## Consequences

- Every builder path that mints a URN must clean segments with `urn_safe_leaf`, take default ids as the highest number + 1, and suffix generated ids with `-N` on collision. The one exception is live framework adoption, which keeps filling missing question and choice ids by position.
- A default question id must never repeat the requirement's ref_id.
- The end of an existing URN must never be rewritten; only renaming an unpublished draft may change its start. Any change to this scheme applies to new URNs only.
- Every new way of creating a draft identity must enforce the 32-character packager, except adoption, which keeps the original identity.
- Validate and publish remain the only URN length gate. An author can still reach an over-long URN with very long ref_ids and only learn it at Validate; `live.py` writes live rows directly, so an over-long URN there fails on the database itself.
- Authors can rely on the CEL key contract above. Showing the key in the editor is deferred: the editor only knows the temporary URN of a new item until it is reloaded, so the save must first return the minted URNs.
- URNs minted by the Excel converter still differ (questions numbered by position, requirement ids from the name, `:` kept). Aligning the converter is a separate decision.

## Security considerations

- Nothing changes in who can create or read libraries; the packager alphabet is unchanged.
- URNs bind audit answers to questions and choices on republish. Never rewriting published URNs keeps answers attached to the questions they were given for.
- Taking the highest number + 1 stops a new question or choice from reusing the URN of one deleted earlier, except when the deleted one was the highest. In that case, republishing a published library attaches the old answers (or choice selections) to the new item. We accept this risk; recording the URNs of the last published version would remove it.
- CEL keys are string literals evaluated by the existing sandboxed CEL engine; deriving them from ref_ids adds no evaluation path.

## Alternatives considered

- **Shorten over-long segments with a hash, keeping room for the children** (first version of #4935): changes identities and CEL keys, and needs a second rule for renames.
- **Cut every URN over 255 characters and append a hash**: question URNs would no longer start with their requirement's, so renames stop moving them; a choice ref_id derived from a cut URN can exceed the 100-character column.
- **Cap every segment at 32 characters with a hash**: same identity churn, and 101 shipped library ref_ids already exceed 32.
- **Per-segment caps that guarantee 255 by construction** (library 50, requirement 100, question 32): constrains what authors can type, which we chose not to do.
- **Number questions by position and ignore their ref_id**, as the converter does: authors can no longer name a question and use the name in a CEL rule, which quick forms rely on.
- **Refuse at save any change that adds a URN over 255 characters**: possible later; not worth the extra code for cases this rare.
- **Repair over-long URNs in existing drafts**: requires rewriting the keys used in CEL rules; deferred.
- **One scheme for every producer, converter included**: shipped content fits the limit and the converter keeps compatibility modes for existing files; separate work.
- **A name slug for requirements without ref_id**: names can be up to 200 characters; `node{N}` is short and stable.

## Annex A — URN producers (behaviour before this ADR)

| Producer | Requirement | Question | Choice | Other objects | Collision | Length check |
|---|---|---|---|---|---|---|
| Builder editor (`library/framework_editor.py`, quick forms included) | `{base}:{ref_id}`, else the name, else `node{position}` | `{node}:question:{ref_id}`, else its position | `{question}:choice:{n}`, lowest free `n` | — | `-N` | none at save |
| Builder: framework / quick form creation (`library/views.py`) | first page `page-1` | — | — | `urn:{packager}:risk:{type}:{library}` | — | packager |
| Builder: add object (`upsert-object`) | — | — | — | `{base}:{ref_id}`, bare for a singleton | refused (409) | none |
| Builder: rename, import objects (`library/builder.py`) | keeps the old suffix | follows its requirement | follows its question | `{base}:{ref_id}` | `-N` | none |
| Live framework adoption (`library/live.py`) | `{base}:{ref_id}`, else the name, else `node{position}` | `:question:{position}` | `:choice:{position}` | framework `urn:{packager}:risk:framework:{ref}` | `-N`, database checked | none |
| Frontend (`builder-state.ts`), temporary | `urn:{ns}:risk:req_node:{slug}:{ref_id}` | `…:question:{slug}:{ref_id}` | `…:question_choice:…` | — | `-N` | — |
| *Out of scope:* Excel converter (`backend/scripts/convert_library_v2.py`) | `node_id` column, ref_id, `{parent}:{n}`, name or `node{n}` | `:question:{position}` | `:choice:{position}` | `{base_urn}:{ref_id}` | error | none |
| *Out of scope:* `tools/excel` scripts | write base URNs into the Excel files; the converter does the rest | | | | | |
| *Out of scope:* workflow export | — | — | — | `urn:custom:risk:library:workflow-{leaf}:workflow:{leaf}` | — | none |

Checks shared by all: the 255-character URN columns, `URN_REGEX` on the library URN at load, and `_check_field_lengths` (name 200, ref_id 100, URN 255) at Validate and publish for drafts.

## Annex B — shipped libraries (`backend/library/libraries`, 333 files)

| Measure | Value |
|---|---|
| Minted URNs (objects, requirements, questions, choices) | 88,517 |
| Longest URN | 172 characters; none over 200, 30 over 150 |
| Longest packager | 18 characters (`intuitem` for 79,462 URNs) |
| Library ref_id | up to 83 characters; 101 over 32, 11 over 50 |
| Requirement id segment | 141 over 32 characters, 3 over 100 |
| Requirement ids with nested `:` | 5,313 requirements in 32 libraries |
| Question ids | 3,763 numbers, 22 names (longest: `compensating_control`, 20) |
| Choice ids | 9,251 numbers, 27 others |
| Legacy type tokens | `function` (552), `reference-controls` (192), `requirement_mapping_set` (1) |
| Library URNs outside `urn:<pkg>:risk:library:<ref>` | 11 |
