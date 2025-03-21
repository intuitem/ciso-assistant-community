<script lang="ts">
	import RadarChart from '$lib/components/Chart/RadarChart.svelte';
	import FlippableCard from './FlippableCard.svelte';
	import type { PageData } from './$types';
	export let data: PageData;
</script>

{@debug data}
<div class="card bg-white bg-stripes-pink">
	<div class="p-6 bg-white bg-opacity-95">
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
			{#each data.data as provider}
				<FlippableCard {provider} />
			{/each}
		</div>
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
