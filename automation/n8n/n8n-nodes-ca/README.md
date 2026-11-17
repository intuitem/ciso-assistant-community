# @intuitem/n8n-nodes-ciso-assistant

n8n community node for [CISO Assistant](https://github.com/intuitem/ciso-assistant-community).

This is the official package, published from this repository with npm provenance. The unscoped `n8n-nodes-ciso-assistant` package on npm is not maintained by intuitem.

Full guide: [n8n node in the CISO Assistant documentation](https://intuitem.gitbook.io/ciso-assistant/ai-and-integrations/n8n).

## Installation

On self-hosted n8n: **Settings → Community Nodes → Install**, then enter `@intuitem/n8n-nodes-ciso-assistant`.

n8n Cloud only offers community nodes that n8n has verified, from the nodes panel. This one isn't verified yet.

For queue mode or manual installs, see the [n8n community nodes installation guide](https://docs.n8n.io/integrations/community-nodes/installation/).

## Credentials

Create a **CISO Assistant API** credential:

- **Personal Access Token (PAT)**: created from your CISO Assistant user profile
- **API URL**: your instance's API base URL, without a trailing slash (e.g. `https://ciso.example.com/api`)
- **Skip TLS Verification**: off by default. Only enable it for self-signed certificates on a trusted network.

The credential test calls `GET /build/` with the token.

## Resources

- System (build info, users)
- Domains, Perimeters, Assets
- Audits (compliance assessments) and requirement assessments
- Risk Assessments, Risk Scenarios, Risk Matrices
- Incidents, Vulnerabilities
- Applied Controls, Task Definitions and Occurrences
- Findings Tracking and Findings, Security Exceptions
- Evidence (with revisions)
- Entities, Solutions, Representatives, Entity Assessments (TPRM)
- Right Requests, Data Breaches (Privacy)
- Frameworks

Every resource except System has Get (by ID) and Get Many. Most also have Create, Update and Get by Name, and some add their own actions (initiating an audit, submitting an evidence revision). The node is usable as an AI agent tool.

Names are case-sensitive for "Get by Name" operations, and dates use ISO 8601.

### Node versions

New nodes use version 2: Get Many and lookups return one item per record, so downstream nodes run once per object. Nodes added before version 2 stay on version 1, which returns a single item with `count` and `results`. To switch a version 1 node, delete it, add it again and replace any `results` expressions downstream.

## Examples

- **Evidence collection**: a Schedule Trigger exports a report from another tool, then **Evidence → Submit Revision** with Revision Type **File Upload** attaches it to an evidence. Set Binary Property to the field holding the file (`data` by default).
- **Audit from a scanner**: map each scanner check to a requirement ref ID, then **Audit → Update Requirement Assessment** sets its result and observation. On version 2, fields left on "No Change" keep their current value.
- **Incident intake**: a Webhook node receives an alert from your ticketing or monitoring tool, then **Incident → Create** records it.
- **AI agent**: attach the node to an AI Agent as a tool so the agent can look up audits, risks or controls when answering questions.

## Development

Requires Node.js 22+.

```bash
npm ci
npm run dev      # starts a local n8n with this node linked, rebuilds on change
npm run lint
npm test
npm run build
```

To load a build into an existing n8n instead, point `N8N_CUSTOM_EXTENSIONS` at this directory, or mount it in the container (for example `-v $PWD:/custom-nodes -e N8N_CUSTOM_EXTENSIONS=/custom-nodes`). Nodes loaded this way get the type `CUSTOM.cisoAssistantService`. Nodes installed from npm get `@intuitem/n8n-nodes-ciso-assistant.cisoAssistantService`, so existing workflows have to swap their nodes when moving from one to the other.

## Releasing

Releases are published by `.github/workflows/n8n-node.yml` with no npm token stored anywhere. GitHub's OIDC token is exchanged with npm (trusted publishing), and the package gets a provenance statement linking it to the commit and workflow that built it.

1. Open a PR that bumps `version` in `package.json` and adds a `CHANGELOG.md` entry.
2. Once it's merged, tag the merge commit and push the tag:
   ```bash
   git tag n8n-v1.2.3 <merge-sha> && git push origin n8n-v1.2.3
   ```
3. The job checks that the tag matches `package.json`, then lints, builds and publishes. Only organization admins can create `n8n-v*` tags (repository tag ruleset).

`npm publish` from a workstation is blocked by the `prepublishOnly` guard. Don't work around it: a package published without provenance can't be verified by n8n.

## License

[MIT](LICENSE.md). The rest of this repository is under its own [licenses](../../../LICENSE.md).

"CISO Assistant" and the CISO Assistant logo are trademarks of intuitem. The MIT license covers this package's code and does not grant rights to use them.
