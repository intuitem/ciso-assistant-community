# Deploy a metric definition to domains and monitor its collection

- Status: Proposed
- Date: 2026-11-03
- Deciders: @nas-tabchiche

## Context

A group measuring one metric across subsidiaries defines it once, then creates an instance per domain by hand, repeating its settings each time. Collection frequency lives on the instance only. Once deployed, nothing shows which domains have recorded for the period, or lets the group check the values. A dashboard widget links to nothing.

Creating a metric in one form, and the definition's direction and decimals, are decided in [one-step-metric-creation](one-step-metric-creation.md). The period on entered samples and the collection task that reminds and tracks are decided in [metric-collection-through-tasks](metric-collection-through-tasks.md). Combining instances across a subtree is decided in [derived-metrics-from-other-metrics](derived-metrics-from-other-metrics.md).

## Decision

A definition is deployed to domains from its page: pick sub-domains, set frequency, target, owner and status once, and one instance per selected domain is created, named "Definition · Domain", each with its collection task. Domains that already have an instance are left unchanged. Deployment is one-shot: a sub-domain added later shows as not deployed.

The definition gains a default collection frequency beside its default target. Both are copied at deployment, never pushed to existing instances.

A definition page shows its collection: its instances in the subtree by period, with missing, late and jump markers, a jump being a move over a fixed share from the previous period. Missing and late come from the collection occurrences. A cell opens the sample, with its observation and evidence, which can be marked checked.

A widget opens a drawer with its series and per-domain values. It links to the instance for a custom widget, to the object for a built-in one, and to the definition's collection view for an aggregated one. There is no per-widget link setting.

## Consequences

- A domain where the user may not add metrics is listed but cannot be selected.
- Changing a definition default changes nothing already deployed.
- Deployment asks for an owner, since an instance without one reminds nobody.
- The jump threshold is a product constant, not a setting.
- Schema: a default frequency on the definition, in the same migration as the one-step fields. No data step.

## Security considerations

Deployment is checked per target domain, not on the definition. The collection view and the widget drawer show values from instances the reader can already read, the rule aggregated widgets follow. Marking a sample checked needs change rights on the sample.

## Alternatives considered

- Auto-deploying to sub-domains added later. Creates objects nobody asked for in a domain.
- Pushing definition defaults down to existing instances. A group edit silently rewrites settings a domain manager chose.
- Monitoring collection from a dashboard. A dashboard shows values, not who has not recorded.
- A per-widget link setting. The widget's source already says where to go.
