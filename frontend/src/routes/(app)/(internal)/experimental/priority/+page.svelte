<script lang="ts">
	import type { PageData } from './$types';
	export let data: PageData;
	import PriorityRadarChart from '$lib/components/Chart/PriorityRadarChart.svelte';
</script>

<div class="bg-white shadow flex overflow-x-auto">
	<div class="w-full h-screen">
		<PriorityRadarChart title="" name="c_priority" data={data.data} />
	</div>

	{#if data.not_displayed > 0}
		<div>{data.not_displayed} are not shown</div>
	{/if}
</div>
