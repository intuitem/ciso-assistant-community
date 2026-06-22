# General settings

Instance-wide settings that don't belong to a more specific category. Grouped here by intent — the order in the UI may differ.

## Display and interface

- **Security objective scale** — the labels used for ratings of security objectives (e.g. C/I/A).
- **EBIOS radar configuration** — the max radius and the green / yellow / red zone radii used to draw the EBIOS RM radar chart.
- **Aggregated scenario matrix** — toggles the aggregated view of scenarios on the risk-matrix display.
- **Risk matrix axis options** — `swap axes`, `flip vertical`, custom axis labels. Cosmetic adjustments to how every risk matrix is rendered.

## Language

- **Default language** — fallback locale for users who haven't picked a preference and for system-generated emails. Must be one of the languages enabled in the instance build.

## Money

- **Currency** — the unit used when displaying applied-control costs and quantitative-risk amounts.
- **Daily rate** — default daily cost used when expressing effort in monetary terms.
- **Conversion rate** — write-only field used when changing the currency to convert existing cost amounts in one operation.

> When you change the currency with a conversion rate, the platform sweeps every applied control's cost structure and applies the conversion. Without a conversion rate it just relabels — the numbers stay the same.

## Behaviour

- **Allow self-validation** — whether a user can validate workflows they themselves created. Off by default for separation-of-duty reasons.
- **Show warning on external links** — interstitial prompt before opening links that leave the platform.
- **Enforce MFA** — make multi-factor authentication mandatory for every user account.
- **Allow assignments to entities** — whether requirements and tasks can be assigned to third-party entities (not just internal users).
- **Mapping max depth** — how many frameworks a chained mapping path may span when projecting one framework onto another, counted as nodes in the path (2–5, default 3). A value of 3 allows one pivot — A → B → C. See [transitive inference](../../concepts/mappings.md#transitive-inference-pivot-mappings).

## Retention

- **Built-in metrics retention (days)** — how long built-in metric samples are kept before being aged out. Minimum 1.

## Notifications

- **Enable email notifications** — master switch for outbound email notifications. See also [Setting up mailer](../../installation/mailer.md).

## AI / LLM provider

These settings drive the optional AI features (chat mode, agentic workflows, RAG over the knowledge base):

- **LLM provider** — which provider the platform calls (Ollama, OpenAI, …).
- **Ollama** — base URL, model, embedding model. Used when the provider is Ollama.
- **OpenAI** — API base, model, API key (write-only; never returned by GET). Used when the provider is OpenAI.
- **Embedding backend** — which backend powers semantic search over knowledge.
- **Chat system prompt** — system prompt prepended to chat-mode conversations.

{% hint style="warning" %}
**Local or self-hosted LLMs.** The **Ollama URL** and OpenAI **API base URL** are checked when you save them and must resolve to a public address — private, loopback, and internal IPs are rejected to prevent server-side request forgery (SSRF). To point at a local or in-network model (for example Ollama on `localhost`, LM Studio, or an in-cluster endpoint), start the backend with the environment variable `ALLOW_PRIVATE_NETWORK_REQUESTS=True`. (This variable was previously named `WEBHOOK_ALLOW_PRIVATE_IPS`; the old name is no longer recognized.)
{% endhint %}

## Analytics

- **Default custom analytics dashboard** — UUID of the dashboard shown by default on the analytics page.

## Domain-tree audit inheritance

Shown only when the **Domain-tree audit inheritance** feature flag is on (under the **Compliance assessments** group).

- **Domain inheritance strategy** — when the same framework is audited at several levels of the domain tree, decides how a child audit combines results with its parent audits. Options: _No inheritance_ (default), _Parent always wins_, _Child always wins_, _Best case (optimistic)_, _Worst case (prudent)_. Scores from a different scale are normalised to the top parent's scale. This one org-wide setting drives the **Combined view** on the [Framework report](../../features/framework-report.md#combined-view-domain-tree-inheritance) and the inheritance panel in [Advanced Analytics](../../features/audit-analytics.md). Leaving it on _No inheritance_ keeps the feature dormant even with the flag enabled.
