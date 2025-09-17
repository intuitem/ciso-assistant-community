<script lang="ts">
	import type { PageData } from './$types';
	import PriorityRadarChart from '$lib/components/Chart/PriorityRadarChart.svelte';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="bg-white shadow flex overflow-x-auto">
	<div class="w-full h-screen">
		<PriorityRadarChart title="" name="c_priority" data={data.data} />
	</div>
</div>
