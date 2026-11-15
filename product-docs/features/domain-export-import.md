# Domain export/import

Pro users (eg. consultants) can export a full domain with its affiliated objects, and anyone, on Pro or Community, can import it into another instance. It is how a consultant hands a client the work done for them, or how a domain moves between instances.

## Export a domain

Open the domain and click **Export**. The download is a ZIP holding the domain's data and the files of its evidences.

<figure><img src="../.gitbook/assets/image (1) (2) (1).png" alt=""><figcaption></figcaption></figure>

The export takes the domain and its sub-domains, flattened into one, with everything that lives in them:

- **Governance and risk** — perimeters, campaigns, risk assessments and their scenarios, risk acceptances, security exceptions, EBIOS RM studies with all their workshop objects, and the risk matrices they use.
- **Compliance** — audits with their requirement assessments and answers, the frameworks they follow, findings binders and findings.
- **Operations** — assets, applied controls, reference controls, threats and techniques, vulnerabilities, incidents, task definitions and occurrences, evidences with their revisions.
- **Third parties** — entities, solutions and their subcontractors, contracts, representatives, entity assessments with the questionnaire audits and quick form responses behind them, and the third-party workspaces those audits live in.
- **Libraries** — the loaded libraries the objects come from.

Every kind of object needs your permission to view it: if you can't view one of them in the domain, the export is refused.

## Import a domain

<figure><img src="../.gitbook/assets/image (1) (2) (1) (1).png" alt=""><figcaption></figcaption></figure>

On the domains list, click **Import domain**, give the new domain a name, and pick the exported file (JSON or ZIP). Two options:

- **Load missing libraries** — load the libraries the export relies on when they aren't loaded on this instance yet.
- **Create missing asset classes** — create the asset classes the exported assets use when this instance doesn't have them. They join the global catalogue, visible to every user.

The import always creates a new domain. When an imported object's name clashes with an existing one, a unique suffix is appended to the clashing name; if the clash can't be solved that way, the import fails with an error.

The third-party workspaces and their questionnaires come back, but not who may access them: respondents' access is not part of the export. Set the representatives' access up again before sending the questionnaires.
