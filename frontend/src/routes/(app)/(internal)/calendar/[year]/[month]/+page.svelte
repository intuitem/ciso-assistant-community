<script lang="ts">
	import { page } from '$app/stores';
	import Calendar from '$lib/components/Calendar/Calendar.svelte';
	import type { PageData } from './$types';

	export let data: PageData;

	$: year = parseInt($page.params.year);
	$: month = parseInt($page.params.month);

	function createCalendarEvents(
		appliedControls: Record<string, string>[],
		riskAcceptances: Record<string, string>[],
		tasks: Record<string, string>[]
	): Array<{ label: string; date: Date; link: string }> {
		const events = [
			...appliedControls.map((control: Record<string, string>) => ({
				label: `AC: ${control.name}`,
				date: new Date(control.eta),
				link: `/applied-controls/${control.id}`
			})),
			...riskAcceptances.map((ra: Record<string, string>) => ({
				label: `RA: ${ra.name}`,
				date: new Date(ra.expiry_date),
				link: `/risk-acceptances/${ra.id}`
			})),
			...tasks.map((task: Record<string, string>) => ({
				label: `Task: ${task.name}`,
				date: new Date(task.due_date),
				link: `/task-templates/${task.id}`
			}))
		];
		return events;
	}

	$: info = createCalendarEvents(data.appliedControls, data.riskAcceptances, data.tasks);
</script>

<Calendar {info} {year} {month} />
