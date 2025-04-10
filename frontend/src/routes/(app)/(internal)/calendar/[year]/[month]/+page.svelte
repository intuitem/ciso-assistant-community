<script lang="ts">
	import Calendar from '$lib/components/Calendar/Calendar.svelte';

	export let data;
	const appliedControls = data.appliedControls;
	const riskAcceptances = data.riskAcceptances;
	const tasks = data.tasks;
	let info: object[] = [];

	for (let i = 0; i < appliedControls.length; i++) {
		const date = new Date(appliedControls[i].eta);
		info.push({
			label: 'AC: ' + appliedControls[i].name,
			date: date,
			link: `/applied-controls/${appliedControls[i].id}`
		});
	}
	for (let i = 0; i < riskAcceptances.length; i++) {
		const date = new Date(riskAcceptances[i].expiry_date);
		info.push({
			label: 'RA: ' + riskAcceptances[i].name,
			date: date,
			link: `/risk-acceptances/${riskAcceptances[i].id}`
		});
	}
	for (let i = 0; i < tasks.length; i++) {
		const date = new Date(tasks[i].task_date);
		info.push({
			label: 'Task: ' + tasks[i].name,
			date: date,
			link: `/task-nodes/${tasks[i].id}`
		});
	}
</script>

<Calendar {info} />
