<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import RadarChart from '$lib/components/Chart/RadarChart.svelte';
	const data = [
		{ name: 'Provider 1', framwork: 'xyz', solution: 'abc', progress: 85, conclusion: 'blocker' },
		{ name: 'Provider 1', framwork: 'xyz', solution: 'abc', progress: 85, conclusion: 'blocker' },
		{ name: 'Provider 1', framwork: 'xyz', solution: 'abc', progress: 85, conclusion: 'blocker' },
		{ name: 'Provider 1', framwork: 'xyz', solution: 'abc', progress: 85, conclusion: 'blocker' },
		{ name: 'Provider 1', framwork: 'xyz', solution: 'abc', progress: 85, conclusion: 'blocker' },
		{ name: 'Provider 1', framwork: 'xyz', solution: 'abc', progress: 85, conclusion: 'blocker' },
		{ name: 'Provider 1', framwork: 'xyz', solution: 'abc', progress: 85, conclusion: 'blocker' },
		{ name: 'Provider 1', framwork: 'xyz', solution: 'abc', progress: 85, conclusion: 'blocker' }
	];
</script>

<div class="card bg-white bg-stripes-pink">
	<div class="grid grid-cols-3 lg:grid-cols-5 p-6 gap-6 bg-white bg-opacity-95">
		{#each data as provider}
			<div class="border-purple-300 border-2 bg-white shadow-lg rounded-lg z-30 p-2">
				<div class="font-black">{provider.name}</div>
				<div class="font-semibold mb-2">{provider.solution}</div>
				<div class="mb-2"><span class="code">Baseline: {provider.framwork}</span></div>
				<div>Completion: {provider.progress}</div>
				<div class="text-sm">Last update: yyyy-mm-dd</div>
				<div class="text-sm">Due date: yyyy-mm-dd</div>
				<div class="text-xl text-right">Conclusion: A/B/C</div>
			</div>
		{/each}
	</div>
</div>

<style>
	.bg-stripes-pink {
		background-image: linear-gradient(
			135deg,
			#07275e 10%,
			transparent 0,
			transparent 50%,
			#07275e 0,
			#07275e 60%,
			transparent 0,
			transparent
		);
		background-size: 7.07px 7.07px;
	}
</style>
