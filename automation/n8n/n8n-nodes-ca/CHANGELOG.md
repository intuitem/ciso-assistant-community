# Changelog

## 1.0.0

First release on npm as `@intuitem/n8n-nodes-ciso-assistant`.

- Rebuilt on `@n8n/node-cli` (strict mode): `n8n-node build`/`lint`, published with npm provenance.
- Credential: authentication and connection test are handled by n8n. **Skip TLS Verification now defaults to off**, so re-enable it on credentials that connect to an instance with a self-signed certificate.
- API errors are reported as n8n API errors, keeping the HTTP status and response body.
- Node is usable as an AI agent tool.
- **Node version 2** (default for new nodes): Get Many and lookup operations (Get by Name, Get by Ref ID, Get User by Email, requirement assessments, evidence revisions) output one item per record instead of a single `{count, results}` item, and no matches means no items. Nodes already in saved workflows stay on version 1 and keep the old output.
- New **Get** operation (by ID) on every resource except System. "List" is labelled "Get Many".
- Listing requirement assessments and evidence revisions now pages through all results instead of stopping at the server's page size.
- Fixed Task Definition and Task Occurrence, which called endpoints that don't exist (`task-definitions`, `task-occurrences`) and always failed. They now use `task-templates` and `task-nodes`.
- Options in dropdowns are listed alphabetically. The Entity Assessment conclusion gains an explicit "Not Set" choice, which is its existing default.
- License changed to MIT.
