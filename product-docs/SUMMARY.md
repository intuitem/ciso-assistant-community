# Table of contents

* [Welcome](README.md)

## Introduction

* [Philosophy](introduction/philosophy.md)
* [Vocabulary](introduction/vocabulary.md)
* [Community vs PRO](introduction/editions.md)

## Concepts

* Foundations
  * [Domains](concepts/domains.md)
  * [Perimeters](concepts/perimeters.md)
  * [Actors and teams](concepts/actors-and-teams.md)
  * [IAM and scoping](concepts/iam-and-scoping.md)
* Catalog
  * [Libraries](concepts/libraries.md)
  * [Frameworks](concepts/frameworks.md)
  * [Mappings](concepts/mappings.md)
  * [Risk matrices](concepts/risk-matrices.md)
  * [Threats](concepts/threats.md)
  * [Threat intelligence](concepts/threat-intel.md)
  * [Metrics](concepts/metrics.md)
  * [Journeys](concepts/journeys.md)
* Assets and resilience
  * [Assets](concepts/assets.md)
  * [Business impact analyses](concepts/business-impact-analyses.md)
* Operations
  * [Applied controls](concepts/applied-controls.md)
  * [Tasks](concepts/tasks.md)
  * [Incidents](concepts/incidents.md)
* Governance
  * [Policies](concepts/policies.md)
  * [Findings assessments](concepts/findings-assessments.md)
  * [Validation flows](concepts/validation-flows.md)
* Risk
  * [Risk assessments](concepts/risk-assessments.md)
  * [EBIOS RM](concepts/ebios-rm.md)
  * [Quantitative risk studies](concepts/quantitative-risk-studies.md)
  * [Vulnerabilities](concepts/vulnerabilities.md)
* Compliance
  * [Audits](concepts/audits.md)
    * [Manage extended result](concepts/extended-results.md)
  * [Evidence](concepts/evidence.md)
* Specialised modules
  * [Third-party risk](concepts/third-party-risk.md)
  * [Privacy register](concepts/privacy-register.md)
  * [Project management](concepts/project-management.md)
  * [Terminology](concepts/terminology.md)

## Installation

* [Overview](installation/README.md)
* [Quick start](installation/quick-start.md)
* [Prerequisites](installation/prerequisites.md)
* Deployment methods
  * [Local](installation/local.md)
  * [Docker rootless configuration](installation/docker-rootless.md)
  * [Remote/Virtualization](installation/remote-virtualization.md)
  * [Deploy on a VPS](installation/vps.md)
  * [Windows](installation/windows.md)
  * [Helm Chart](installation/helm-chart.md)
* Post-install setup
  * [Custom certificates](installation/custom-certificates.md)
  * [Managing secrets](installation/managing-secrets.md)
  * [Setting up S3](installation/s3.md)
  * [Setting up mailer](installation/mailer.md)
  * [Prometheus metrics](installation/prometheus-metrics.md)
  * [Structured logging](installation/structured-logging.md)
* Maintenance
  * [Updating your local instance](installation/updating.md)
  * [Special cases](installation/special-cases.md)
  * [Migrate between different databases](installation/migrate-database.md)
* [Frequent questions](installation/faq.md)

## Configuration

* [Overview](configuration/README.md)
* [Settings](configuration/settings/README.md)
  * [General settings](configuration/settings/general.md)
  * [Feature flags](configuration/settings/feature-flags.md)
  * [Vulnerability SLA policy](configuration/settings/vulnerability-sla.md)
  * [Security intelligence feeds](configuration/settings/sec-intel-feeds.md)
  * [Allowed IP whitelist](configuration/settings/infra-config-allowed-ip.md)
  * [Branding](configuration/settings/branding.md)
  * [Custom templates](configuration/settings/custom-templates.md)
* [Organization](configuration/organization/README.md)
  * [Add and manage users](configuration/organization/users.md)
  * [User groups](configuration/organization/user-groups.md)
  * [Custom roles](configuration/organization/custom-roles.md)
  * [Understanding the IAM model](configuration/organization/iam-model.md)
  * [Teams](configuration/organization/teams.md)
* [SSO](configuration/sso/README.md)
  * [SAML](configuration/sso/saml.md)
  * [OpenID Connect (OIDC)](configuration/sso/oidc.md)
  * [Identity providers](configuration/sso/identity-providers/README.md)
    * [Microsoft Entra ID](configuration/sso/identity-providers/entra-id.md)
    * [Okta](configuration/sso/identity-providers/okta.md)
    * [Google Workspace](configuration/sso/identity-providers/google-workspace.md)
    * [Keycloak](configuration/sso/identity-providers/keycloak.md)
* [Multi-Factor Authentication (MFA)](configuration/mfa.md)
* [Libraries](configuration/libraries/README.md)
  * [Designing your own libraries](configuration/libraries/custom-libraries.md)
  * [Getting your custom framework](configuration/libraries/custom-frameworks.md)
  * [CIS Controls / Cloud Controls Matrix (CCM)](configuration/libraries/cis-controls.md)
  * [Library upgrade](configuration/libraries/library-upgrade.md)
  * [Upgrading a library](configuration/libraries/upgrading-a-library.md)
  * [Library clean-up](configuration/libraries/library-cleanup.md)
* [Authoring](configuration/authoring/README.md)
  * [Framework](configuration/authoring/framework.md)
    * [Framework builder — reference](configuration/authoring/framework-builder.md)
  * [Risk matrix](configuration/authoring/matrix.md)
    * [Matrix editor — reference](configuration/authoring/matrix-editor.md)
  * [Journey preset](configuration/authoring/preset.md)
    * [Preset editor — reference](configuration/authoring/preset-editor.md)
  * [Excel-driven authoring](configuration/authoring/excel.md)
* [Data import wizard](configuration/data-import.md)
* [Changing the language](configuration/language.md)
* [Date format](configuration/date-format.md)

## Guides

* [Overview](guides/README.md)
* [General tips](guides/general-tips.md)
* Getting started
  * [Initial setup](guides/initial-setup.md)
  * [Creating your first perimeter](guides/first-perimeter.md)
  * [Creating your first audit](guides/first-audit.md)
  * [Creating your first risk assessment](guides/first-risk-assessment.md)
* Assessments
  * [Basic audit](guides/basic-audit.md)
  * [Customize your audit](guides/customize-audit.md)
  * [EBIOS RM study](guides/ebios-rm.md)
  * [Cyber risk quantification](guides/quantitative-risk.md)
  * [Cyber risk quantification — methodology](guides/quantitative-risk-methodology.md)
  * [Conducting a Business Impact Analysis](guides/bia.md)
* Programme management
  * [Managing a project](guides/projects.md)
  * [Managing a collection](guides/collections.md)
  * [Managing an accreditation](guides/accreditations.md)
  * [Managing a responsibility matrix](guides/responsibility-matrix.md)
* Third-party
  * [Third-Party Risk Management](guides/tprm.md)

## Features

* [Catalogue overview](features/README.md)
* [Analytics](features/analytics.md)
* [Controls autosuggestion](features/controls-autosuggestion.md)
* [Multi-level support](features/multi-level-support.md)
* [Flash mode](features/flash-mode.md)
* [Kanban mode](features/kanban-mode.md)
* [Applied controls analytics](features/applied-controls-analytics.md)
* [Evidences from clipboard](features/evidences-from-clipboard.md)
* [Mappings](features/mappings.md)
* [Mapping explorer](features/mapping-explorer.md)
* [X-rays](features/x-rays.md)
* [Scoring Assistant](features/scoring-assistant.md)
* [Assignments / respondent mode](features/assignments.md)
* [Comments](features/comments.md)
* [Audit log](features/audit-log.md)
* [Domain export/import](features/domain-export-import.md)
* [Focus mode](features/focus-mode.md)
* [Sync to actions](features/sync-to-actions.md)
* [Dashboards](features/dashboards.md)
* [Audit advanced analytics](features/audit-analytics.md)
* [Framework report](features/framework-report.md)
* [Insights](features/insights.md)
* [Control Plan](features/control-plan.md)
* [Action plans](features/action-plans.md)
* [Working with tables](features/working-with-tables.md)
* [Command palette](features/command-palette.md)
* [Universal search](features/search.md)
* [My assignments](features/my-assignments.md)
* [Notifications](features/notifications.md)
* [Framework-specific features](features/framework-specific/README.md)
  * [ISO 27001](features/framework-specific/iso.md)
  * [CCB CyFun](features/framework-specific/cyfun.md)
  * [DORA](features/framework-specific/dora.md)
  * [MonServiceSécurisé](features/framework-specific/monservicesecurise.md)

## AI and Integrations

* [Overview](integrations/README.md)
* [API reference](integrations/api.md)
* [Generating a PAT](integrations/pat.md)
* [Outgoing webhooks](integrations/webhooks.md)
* [MCP setup guide](integrations/mcp.md)
* [Third-party integrations](integrations/third-party/README.md)
  * [Jira](integrations/third-party/jira.md)
  * [ServiceNow](integrations/third-party/servicenow.md)

## Contributing

* [Overview](contributing/README.md)
* [Frameworks and libraries](contributing/framework.md)
* [Code (features and fixes)](contributing/code.md)
* [Translations](contributing/translation.md)
* [Documentation](contributing/documentation.md)
* [Feature page template](contributing/feature-page-template.md)
