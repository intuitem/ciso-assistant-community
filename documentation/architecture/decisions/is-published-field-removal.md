# Remove all the object is_published fields (replaced by a single Folder.viewable_from_descendants field).

- Status: Accepted
- Deciders: @eric-intuitem, @monsieurswag, @nas-tabchiche

## Context

Some objects need to be published (viewable from descendant folders), that's why the `is_published` boolean field has been added to almost all our models (159 over 168).
Most models need their objects to be either never published or always published (which make most `is_published` fields useless in practice).
Only a few models would benefit from customizable (user-controlled) object publication.

## Decision

- We will remove the `is_published` field from all objects.
- We will add the `ViewableFromDescendantsMode` enum with 3 possible values:
  - `ALWAYS_VIEWABLE` will make the model objects be ALWAYS published.
  - `MAY_BE_VIEWABLE` will make the model model objects be published ONLY IF the folder they're in has their `viewable_from_descendants` field set to `True`.
  - `NEVER_VIEWABLE` will make the model objects be NEVER published.

- Each model class will have a `VIEWABLE_FROM_DESCENDANTS_MODE` attribute (the default being `NEVER_VIEWABLE` for safety reasons).

## Consequences

- We remove 158 useless `is_published` columns from the DB.
- We remove the burden of ensuring the consistency of `is_published` values throughout 158 models.
- We avoid having implicit `is_published` rules (they're now explicit with the `ViewableFromDescendantsMode`).

## Alternatives considered

- Add a `Folder.published_models` field ManyToManyField(Folder => ContentType) to decide which models are published for each domain: too complex, could slow down IAM queries a lot.
- Add an extra `Folder.stop_published_propagation` field: too annoying to implement for too little benefits (we alredy have `ENCLAVE` folders).

## Security considerations

A developer changing/setting `SomeModel.VIEWABLE_FROM_DESCENDANTS_MODE` to `ALWAYS_VIEWABLE` by mistake could be dangerous.
This risk is mitigated by defaulting to `NEVER_VIEWABLE` (even when the attribute isn't defined).
This makes it so setting it to `ALWAYS_VIEWABLE` would always be visible in a code review.

A user may set `Folder.viewable_from_descendants` to `True` carelessly (thinking it publishes the folder itself instead of the objects in it).
This risk is mitigated by a descriptive "help message" under the `viewable_from_descendants` checkbox in frontend.
Adding some kind of "warning" modal would be too annoying for users, a good help message is enough.
