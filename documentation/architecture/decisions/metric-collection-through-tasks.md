# Collect entered metrics through tasks

- Status: Proposed
- Date: 2026-11-03
- Deciders: @nas-tabchiche

## Context

An entered sample carries a timestamp only; a formula sample also carries its period. Nothing can say an entered value is for October, or late. A job flags instances as stale, and nobody is told: no reminder, no list of what is due.

Task templates already recur, produce dated occurrences, mail assignees when due or overdue, have a review page, and count in analytics. Sub-daily frequencies are automated collection and need none.

Deployment of a definition and the group's view of its collection are decided in [deploy-definitions-to-domains](deploy-definitions-to-domains.md).

## Decision

An entered sample answers for a period, as a formula sample does. The form defaults it from the frequency, and a value entered for a period that has one replaces it. A metric without a frequency keeps timestamp-only samples; existing samples are read by the period their timestamp falls in.

A period is the calendar unit of the frequency: day, ISO week, month, quarter, year. Its value is due a number of days after it ends, the grace, held on the metric and defaulted by frequency: 1, 2, 5, 15 and 31 days. The first period is the one in progress at creation.

A metric with a frequency and no formula owns one collection task template. It is created with the metric, in its folder, dated at the first due date, scheduled from the frequency, assigned to the owners. Grace, frequency, owner and status changes rewrite it; an inactive metric disables it; deleting the metric deletes it. It is edited through the metric only. An occurrence's period is derived from its date and the grace, never stored.

Recording a value for a period completes that period's occurrence. Closing one by hand means no value this period, the observation saying why. Due, late and reminders are the task module's.

## Consequences

- A reporter's inbox is the task review page.
- Owners are the assignees: one field, synced, user or team. A metric without an owner reminds nobody; the collection view marks it.
- Collection tasks are flagged so task views can filter them; the due-soon mail is already one per recipient.
- The stale status stays for automated collection.
- Quarterly is monthly with interval three; grace stays under 28 days so month stepping never drifts.
- Schema: a nullable link from the metric to its task template and a grace in days, in the one-step creation migration. The period column and its uniqueness rule exist; no data step.
- The period on entered values and the columns land with the creation release; the task itself a release later.

## Security considerations

The template lives in the metric's folder under its permissions. A reporter needs sample add rights and occurrence change rights in the domain, nothing on the metric. Replacing a period's value needs change rights on the sample. The system completes the occurrence.

## Alternatives considered

- Deriving the period from the timestamp. Wrong for a value typed early in the next period, the common case.
- Reminders of the metric module's own. A second scheduler and inbox for the same need.
- Attaching any existing task template. Its schedule and assignees can disagree with the metric.
- Storing the period on the occurrence. Derivable from its date.
- A due day of the month instead of a grace. Does not transpose to weeks or years.
