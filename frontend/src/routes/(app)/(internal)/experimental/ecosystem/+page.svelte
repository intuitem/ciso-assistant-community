<script lang="ts">
	import type { PageData } from './$types';
	export let data: PageData;
	import PriorityRadarChart from '$lib/components/Chart/PriorityRadarChart.svelte';
</script>

<div class="bg-white shadow flex overflow-x-auto">
	<div class="w-full h-screen">
		<PriorityRadarChart title="Ecosystem - current" name="c_ecosystem" data={data.data.current} />
	</div>
</div>
