<script lang="ts">
	import WorldMap from '$lib/components/DataViz/WorldMap.svelte';
	const data = [{ id: 'FR', age: [12, 12, 12] }];
</script>

<div>
	<WorldMap {data} />
</div>
