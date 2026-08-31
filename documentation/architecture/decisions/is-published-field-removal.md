# Remove all the object is_published fields (replaced by a single Folder.default_role field).

- Status: Accepted
- Deciders: @eric-intuitem, @monsieurswag, @nas-tabchiche

## Context

Some objects need to be published (viewable from descendant folders), that's why the `is_published` boolean field has been added to almost all our models (159 over 168).
Most models need their objects to be either never published or always published (which make most `is_published` fields useless in practice).
Only a few models would benefit from customizable (user-controlled) object publication.

## Decision

- We will remove the `is_published` field from all objects.
- We will add the (nullable) `Folder.default_role` ForeignKey to a `Role` object.
- We will add the "reader catalog" role (which is the most appropriate "default option" for a default role) and a second "reader migration legacy" role (used to minimize the migration blast radius).

If a `user` has a `RoleAssignment` on any descendant of a `folder`, then if this folder has a `default_role` set, the user will be granted the `default_role` permissions on this folder.

## Consequences

- We remove 158 useless `is_published` columns from the DB.
- We remove the burden of ensuring the consistency of `is_published` values throughout 158 models.
- User can choose which folder "publishes" its objects, and what type of objects are published by it.

## Alternatives considered

- Add a `Folder.published_models` field ManyToManyField(Folder => ContentType) to decide which models are published for each domain: too complex, could slow down IAM queries a lot.
- Add an extra `Folder.stop_published_propagation` field: too annoying to implement for too little benefits (we alredy have `ENCLAVE` folders).
- Make some model being "always viewable by descendants" AND add a `Folder.viewable_from_descendants` BooleanField to choose if a domain publishes its objects from "optionally viewable by descendant" models.

## Security considerations

It's the responsability of the domain manager to not change the `Folder.default_role` carelessly, a very explicit "help message" is displayed in the frontend to ensure admins/domain managers understand what this field is doing.

The default role itself doesn't introduce much IAM risks as they're non-recursive anyway.
