<script lang="ts">
	import { page } from '$app/state';
	import Calendar from '$lib/components/Calendar/Calendar.svelte';
	import { CALENDAR_CATEGORIES, type CalendarEvent } from '$lib/components/Calendar/types';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let year = $derived(parseInt(page.params.year));
	let month = $derived(parseInt(page.params.month));

	function createCalendarEvents(): CalendarEvent[] {
		const events: CalendarEvent[] = [
			...(data.appliedControls ?? [])
				.filter((c: any) => c.eta)
				.map((control: any) => ({
					label: control.name,
					date: new Date(control.eta),
					link: `/applied-controls/${control.id}`,
					users: control.owner ?? [],
					category: 'appliedControl' as const,
					status: control.status
				})),
			...(data.riskAcceptances ?? [])
				.filter((ra: any) => ra.expiry_date)
				.map((ra: any) => ({
					label: ra.name,
					date: new Date(ra.expiry_date),
					link: `/risk-acceptances/${ra.id}`,
					users: ra.approver ? [ra.approver] : [],
					category: 'riskAcceptance' as const,
					status: ra.state
				})),
			...(data.audits ?? [])
				.filter((a: any) => a.due_date)
				.map((audit: any) => ({
					label: audit.name,
					date: new Date(audit.due_date),
					link: `/compliance-assessments/${audit.id}`,
					users: audit.authors ?? [],
					category: 'audit' as const,
					status: audit.status
				})),
			...(data.tasks ?? [])
				.filter((t: any) => t.due_date)
				.map((task: any) => ({
					label: task.name,
					date: new Date(task.due_date),
					link: !task.is_recurrent
						? `/task-templates/${task.task_template.id}`
						: `/task-nodes/${task.id}`,
					users: task.assigned_to ?? [],
					category: 'task' as const,
					status: task.status
				})),
			...(data.contracts ?? [])
				.filter((c: any) => c.end_date)
				.map((contract: any) => ({
					label: contract.name,
					date: new Date(contract.end_date),
					link: `/contracts/${contract.id}`,
					users: contract.owner ? [contract.owner] : [],
					category: 'contract' as const,
					status: contract.status
				})),
			...(data.securityExceptions ?? [])
				.filter((se: any) => se.expiration_date)
				.map((se: any) => ({
					label: se.name,
					date: new Date(se.expiration_date),
					link: `/security-exceptions/${se.id}`,
					users: se.owners ?? [],
					category: 'securityException' as const,
					status: se.status
				})),
			...(data.findings ?? [])
				.filter((f: any) => f.due_date)
				.map((finding: any) => ({
					label: finding.name,
					date: new Date(finding.due_date),
					link: `/findings/${finding.id}`,
					users: finding.owner ? [finding.owner] : [],
					category: 'finding' as const,
					status: finding.status
				})),
			...(data.riskAssessments ?? [])
				.filter((ra: any) => ra.due_date)
				.map((ra: any) => ({
					label: ra.name,
					date: new Date(ra.due_date),
					link: `/risk-assessments/${ra.id}`,
					users: ra.authors ?? [],
					category: 'riskAssessment' as const,
					status: ra.status
				}))
		];
		return events;
	}

	let info = $derived(createCalendarEvents());
</script>

<Calendar {info} {year} {month} categories={CALENDAR_CATEGORIES} actorIds={data.actorIds ?? []} />
