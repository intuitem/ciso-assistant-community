<script lang="ts">
	import ImpactEffortMatrix from './ImpactEffortMatrix.svelte';
	let data = [
		{ id: 1, name: 'task1', impact: 1, effort: 1 },
		{ id: 2, name: 'task2', impact: 1, effort: 1 },
		{ id: 3, name: 'task1', impact: 2, effort: 4 },
		{ id: 4, name: 'task1', impact: 3, effort: 3 },
		{ id: 4, name: 'task1', impact: 3, effort: 2 },
		{ id: 4, name: 'task1', impact: 4, effort: 3 },
		{ id: 5, name: 'task1', impact: 4, effort: 5 }
	];
</script>

<ImpactEffortMatrix tasks={data} />
