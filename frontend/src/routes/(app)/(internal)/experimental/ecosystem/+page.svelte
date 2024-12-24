<script lang="ts">
	import type { PageData } from './$types';
	export let data: PageData;
	import EcosystemRadarChart from '$lib/components/Chart/EcosystemRadarChart.svelte';
</script>

{@debug data}
<div class="bg-white shadow flex overflow-x-auto">
	<div class="w-full h-screen">
		<EcosystemRadarChart title="Ecosystem" data={data.data} />
	</div>
</div>
