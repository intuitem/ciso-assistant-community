<script lang="ts">
	import ImpactEffortMatrix from './ImpactEffortMatrix.svelte';
	import ImpactEffortMatrix2 from './ImpactEffortMatrix2.svelte';
	let data = [
		{ id: 1, name: 'task1', impact: 1, effort: 1 },
		{ id: 2, name: 'task2', impact: 1, effort: 1 },
		{ id: 3, name: 'task1', impact: 2, effort: 4 },
		{ id: 4, name: 'task1', impact: 3, effort: 3 },
		{ id: 4, name: 'task1', impact: 3, effort: 2 },
		{ id: 4, name: 'task1', impact: 4, effort: 3 },
		{ id: 5, name: 'task1', impact: 4, effort: 5 },
		{ id: 5, name: 'task10', impact: 0, effort: 0 }
	];
</script>

<ImpactEffortMatrix2 tasks={data} showGrid={false} />
