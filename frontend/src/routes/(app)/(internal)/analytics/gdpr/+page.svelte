<script lang="ts">
	import WorldMap from '$lib/components/DataViz/WorldMap.svelte';
	import Card from './Card.svelte';
	const data = [
		{ id: 'FR', count: 10 },
		{ id: 'MA', count: 10 },
		{ id: 'BE', count: 10 },
		{ id: 'US', count: 10 },
		{ id: 'CH', count: 10 }
	];
</script>

<div class="grid grid-cols-1">
	<div class="grid grid-cols-4 bg-slate-100 p-4 gap-4">
		<Card icon="fa-solid fa-gem" text="Personal data categories identified" count={12} />
		<Card icon="fa-solid fa-file-lines" text="Documented Processings" count={7} />
		<Card icon="fa-solid fa-user-tie" text="Data Recipients" count={5} />
		<Card icon="fa-solid fa-circle-exclamation" text="Incidents" count={2} />
	</div>
	<div>
		<WorldMap {data} />
	</div>
</div>
