<script lang="ts">
	import Schedules from '$lib/components/Schedules/Schedules.svelte';

	export let data;
	const applied_controls = data.applied_controls;
	const risk_acceptances = data.risk_acceptances;
	let info: object[] = [];

	for (let i = 0; i < applied_controls.length; i++) {
		let date = new Date(applied_controls[i].eta);
		info.push({
			label: 'AC: ' + applied_controls[i].name,
			date: date,
			link: `/applied-controls/${applied_controls[i].id}`
		});
	}
	for (let i = 0; i < risk_acceptances.length; i++) {
		let date = new Date(risk_acceptances[i].eta);
		info.push({
			label: 'RA: ' + risk_acceptances[i].name,
			date: date,
			link: `/risk-acceptances/${risk_acceptances[i].id}`
		});
	}
</script>

<Schedules {info} />
