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
		<Card icon="fa-solid fa-gem" text="Personal data categories identified" />
	</div>
	<div>
		<WorldMap {data} />
	</div>
</div>
