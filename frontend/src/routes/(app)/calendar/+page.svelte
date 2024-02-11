<script lang="ts">
	import Calendar from '$lib/components/Calendar/Calendar.svelte';

	export let data;
	const security_measures = data.security_measures;
	const risk_acceptances = data.risk_acceptances;
	let info: object[] = [];

	for (let i = 0; i < security_measures.length; i++) {
		let date = new Date(security_measures[i].eta);
		info.push({
			label: 'SM: ' + security_measures[i].name,
			date: date,
			link: `/security-measures/${security_measures[i].id}`
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

<Calendar {info} />
