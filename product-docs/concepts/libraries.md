# Libraries

A **library** is a bundled set of catalog objects — frameworks, threats, risk matrices, reference controls, mappings, security advisories, CWE entries — distributed as a YAML file.

Libraries are how content gets into CISO Assistant. They make the platform extensible: anything from a regulator's framework to a vendor's threat feed to your organisation's internal control catalogue is just another library.

## Stored vs loaded

A library can be in one of two states:

- **Stored** — the library is known to the instance but its content hasn't been activated yet. It's visible in the libraries store, ready to be loaded on demand.
- **Loaded** — the library is active. Its catalog objects show up across the platform: a loaded framework becomes available when creating an audit; a loaded threat appears in the threats list; loaded reference controls power autosuggestion.

## What's in a library

A library typically contains a single primary object (for example, one framework) but may bundle related ones — a framework alongside its companion reference-control catalogue and its mapping to a sibling framework.

Library content is referenced by **URN** (Uniform Resource Name), an immutable identifier that survives renames and re-imports.

## Built-in, community, and custom

- **Built-in libraries** ship with the platform — over 100 frameworks plus the standard threat, matrix, and reference-control catalogues.
- **Community libraries** are contributed by the open-source community; see [Submit a library](../contributing/submit-a-library.md).
- **Custom libraries** can be built locally and loaded without sharing them, useful for internal frameworks or control sets.

See [Designing your own libraries](../configuration/custom-libraries.md) for the format.

## Lifecycle

Libraries are versioned. When a newer version is available, you can upgrade in place — your existing audits keep using the version they were created with until you migrate them explicitly. See [Library upgrade](../features/library-upgrade.md) and [Library clean-up](../features/library-cleanup.md).

## Related

- [Frameworks](frameworks.md)
- [Threats](threats.md)
- [Vocabulary → Library / Catalog object / URN](../introduction/vocabulary.md)
