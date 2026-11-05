# The library builder mints URNs from ref_ids, numbers default ids after the highest one, and caps the packager at 32 characters

- Status: Proposed
- Date: 2026-10-08
- Deciders: @martinzerty

## Context

A URN is the identity of every library object, requirements, questions and choices included. Publishing updates objects by URN, audit answers attach to them, and mappings and CEL rules refer to them. Every URN column is capped at 255 characters in the database.

In the library builder, a new question's default ref_id was `<requirement ref_id>-q<n>` and a question URN is `<requirement URN>:question:<ref_id>`, so the requirement's ref_id appeared twice in every default question URN. With long ref_ids, question and choice URNs went over 255 characters (CA-1854); saved URNs are frozen and read-only in the editor, so Validate reported the overflow too late to fix. Shipped libraries are far from the limit (longest URN 172, longest packager 18): the overflow comes from content authored in the builder.

## Decision

We keep one minting rule for every builder path, the framework and quick form editors, draft creation, adding objects, renaming a draft, importing objects, and adopting a live framework (`live.py`): segments come from ref_ids cleaned by `urn_safe_leaf`, default ids take the highest number already used plus one, and the packager gets a 32-character cap. We do not guarantee URN length at save time, and we never rewrite the end of an existing URN; only renaming an unpublished draft changes its start. The Excel converter, the `tools/excel` scripts and the workflow export keep their own rules and stay out of scope: their shipped content is far below the limit.

### Scheme

```
library      urn:{packager}:risk:library:{library}
object       urn:{packager}:risk:{type}:{library}[:{object}]
requirement  urn:{packager}:risk:req_node:{library}:{requirement}     (quick form page: qf_page)
question     {requirement URN}:question:{question}
choice       {question URN}:choice:{n}
```

The object segment is omitted for the only object of its kind (framework, quick form, risk matrix). Each segment is a ref_id cleaned by `urn_safe_leaf`: lowercased, each run outside `[0-9a-z[]()._-]` collapsed to a single `-`, never a `:`. A requirement without a ref_id becomes `node{N}`.

### Default ids and collisions

A default id, a `node{N}` requirement, the editor's default question number, a question minted without ref_id, or a choice number, takes the **highest number already used + 1**, never the first free one, so a deleted id comes back only when it was the highest. A generated id already taken gets a `-2`, `-3`… suffix; the check runs per path (the editor and draft paths look in the draft, `live.py` among the sibling rows in the database). Creating an object whose ref_id is already used in the draft is refused (`objectUrnAlreadyExists`, HTTP 409). Exception: adopting a live framework fills missing question and choice URNs by position, as before.

### Length and packager

Length is still checked only by Validate and publish (`_check_field_lengths`), not at save. Removing the repeated ref_id makes overflow rare but still possible with very long ref_ids. The packager is the URN namespace; borrowing RFC 8141's 32-character NID limit, it is capped at 32 characters on every new or changed identity (draft create/update, the `default_packager` setting, the frontend inputs, YAML import). Adopting a stored library or live framework keeps its identity. A value predating the cap keeps saving while it is resubmitted unchanged.

### Existing URNs and CEL keys

The end of an already published, stored or saved URN is never rewritten, even when it predates the scheme (nested `:`, legacy type tokens, named questions); only renaming an unpublished draft rewrites the start. Drafts holding URNs over 255 characters keep them, reported by Validate; to fix one, recreate the item or re-import a shortened YAML. A CEL key is everything after the 5th `:` of the stored URN (`extract_node_id`) and is stable once the item is saved and reloaded.

## Consequences

- Every builder path cleans segments with `urn_safe_leaf`, takes default ids as the highest number + 1, and suffixes collisions with `-N`; live adoption still fills missing ids by position.
- A default question id must never repeat the requirement's ref_id.
- The end of an existing URN is never rewritten; any future change to this scheme applies to new URNs only.
- Every new draft-identity path enforces the 32-character packager, except adoption.
- Validate and publish remain the only length gate; `live.py` writes rows directly, so an over-long URN there fails on the database.

## Security considerations

- Never rewriting published URNs keeps audit answers attached to the questions and choices they were given for.
- Highest + 1 stops a new item from reusing a deleted item's URN, except when the deleted one was the highest number: on republish the old answers then attach to the new item. We accept this risk; recording the last published version's URNs would remove it.
- CEL keys are string literals evaluated by the existing sandboxed engine; deriving them from ref_ids adds no evaluation path.

## Alternatives considered

- **Hash-truncate over-long leaves** (first version of #4935): changes identities and CEL keys, and needs a second rule for renames.
- **Per-segment caps that guarantee 255 by construction**: constrains what authors can type; 101 shipped ref_ids already exceed 32 characters.
- **Number questions by position, ignoring their ref_id** (as the converter does): authors could no longer name a question and use the name in a CEL rule, which quick forms rely on.
- **A name slug for requirements without ref_id**: names reach 200 characters; `node{N}` is short and stable.
- **Refuse at save any new URN over 255 characters**: possible later, not worth the extra code for a case this rare.
- **One scheme for every producer, converter included**: shipped content fits the limit and the converter keeps compatibility modes; separate work.
