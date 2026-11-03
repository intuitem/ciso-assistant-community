# Metrics: user journeys and acceptance budgets

Four journeys, one per person who touches a metric. Each is written as a scenario the finished feature must pass, with a budget. A budget is a ceiling, not a target: a journey that needs more interactions than its budget is not done.

Counting rule: an interaction is one click, one key that moves the flow (Enter, Tab to the next field) or one field typed, whatever its length. Picking a value in a dropdown counts two. Reading counts zero. Time is wall clock for a person who knows the product, from the first interaction to the "done" state.

Decisions these scenarios rely on: [one-step-metric-creation](architecture/decisions/one-step-metric-creation.md), [metric-collection-through-tasks](architecture/decisions/metric-collection-through-tasks.md), [deploy-definitions-to-domains](architecture/decisions/deploy-definitions-to-domains.md). Mockups: the Metrics UX canvas, boards 1 to 9.

## J1. Start measuring something

Who: a domain manager who may add metrics in the domain.
Starts from: the metrics list, or the page of a control, objective or task template the metric is about.

Given I am on the metrics list of ACME Spain,
when I click New metric, type "Number of assets", pick the unit Count and the direction None, and click Create,
then I am on the metric's page, it has no value yet, and the page shows one strip asking for the first value.
When I type 1290 and press Enter,
then the metric shows 1 290 assets as its current value, with today as its date.

Also:
- While I type the name, a readable definition with a similar name and the same kind is offered under the field. Ignoring it costs nothing.
- The word "instance" appears nowhere. "Definition" appears only in the hint and in the link "Start from an existing definition instead".
- Starting from a control page, the metric is linked to the control without a further step.
- Kind Level asks for the levels on the same form; it is the only extra block.

Budget: 7 interactions to the first value, 60 seconds. Today, counted on the current forms: three forms on three pages, about 20 interactions, and the person must know that a definition comes first.

## J2. Record this period's values

Who: a reporter in a domain, who may add samples and change task occurrences, and need not be a manager.
Starts from: the reminder the collection task sends when an occurrence is due soon, or from the tasks review page, or from the metric page.

Given ACME Spain has 10 active metrics collected monthly, each with its collection task assigned to me, and October's occurrences are due,
when I open the Record values sheet from the reminder,
then it lists the 10 metrics with the period October preselected, the previous value next to each empty field, and computed metrics greyed out.
When I type 10 values and click Save,
then the 10 samples exist for October, the 10 occurrences are completed, the sheet shows nothing due, and no overdue notice is sent for October.

Also:
- One metric: on its page, type the value and press Enter. Two interactions, and that period's occurrence is completed.
- A value typed for a period that already has one replaces it, and the sheet says so before saving.
- A period I cannot fill is closed from the sheet with a reason, and the Collection tab shows it as missing with that reason, not as late.
- Late is the occurrence's: an open occurrence past its due date marks the metric late on the sheet, on the metric list and on the Collection tab.
- An observation and an evidence can be attached from the same row without opening another page.
- The collection task is visible on the metric page and nowhere to be set up: it exists because the metric has a frequency and an owner.

Budget: 12 interactions and 2 minutes for a 10-metric cycle, 2 interactions for one value. Today: one context menu and one generic modal per value, no reminder, no period, no occurrence to complete.

## J3. Define once, spread, monitor

Who: a group manager at ACME Group who may add metrics in the sub-domains.
Starts from: the definition page.

Given Training coverage is defined at ACME Group and deployed to Spain only,
when I click Deploy to domains, select all sub-domains, leave the frequency and target at their defaults, and click Deploy,
then France, Germany and Nordics each have an active metric named "Training coverage · Domain", Spain is unchanged, and Asia, where I cannot add metrics, was listed but not selectable.

Given it is mid-November,
when I open the Collection tab,
then I see domains by month, October marked as the current period, Germany late, Italy not deployed, and a value that jumped more than the threshold flagged.
When I click the flagged cell,
then I see the sample, its observation and evidence, and can mark it checked.

Also:
- Deploying is idempotent: running it again creates nothing in domains that already have a metric.
- A domain added to the group later shows as not deployed on the Collection tab, with a Deploy link.
- A widget over the definition can be added to the group dashboard from the definition page in one click.

Budget: 5 interactions and 60 seconds to deploy to any number of domains. 1 interaction from the definition to the list of late domains. 2 interactions from the definition to a suspect value. Today: one instance form per domain and no view of who recorded.

## J4. Read and dig

Who: an executive or an auditor with read access to the group dashboard.
Starts from: the dashboard.

Given the group dashboard shows Training coverage aggregated over four domains,
when I click the widget,
then a drawer shows the series against the target and one row per domain with its value, its date and a late or jump marker.
When I click a domain row,
then I am on that domain's metric page, and the browser back button returns me to the dashboard with the drawer closed.

Also:
- Every widget is clickable, including built-in ones: an audit widget opens the audit, a custom one opens the metric, an aggregated one also links to the Collection tab.
- A reader never reaches a value they could not read on the metric itself.
- Nothing in the drawer needs a widget setting to work.

Budget: 1 interaction from a widget to its explanation, 2 to its source. Today: 0 links.

## Cross-cutting

- No journey shows the words "instance" or "sample" to the person. The sidebar has one entry, Metrics; the definition catalog is a tab.
- Each journey ends in a state that says it ended: the metric page after creation, the empty due list after a cycle, the Collection tab after a deploy, the metric page after a drill-down.
- The product metric for this work is the on-time rate per definition, read from the Collection tab.

## Out of these budgets

- Bringing history in: a paste or file import of value and period onto one metric, and onto a definition across domains. It is the onboarding journey and gets its own scenario once the period decision is implemented.
- Dashboard export and a default dashboard per domain.
