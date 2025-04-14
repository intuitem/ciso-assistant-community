<script lang="ts">
	import type { PageData } from './$types';
	export let data: PageData;
	import GraphExplorer from '$lib/components/DataViz/GraphExplorer.svelte';
	import { pageTitle } from '$lib/utils/stores';
	pageTitle.set('Visual Analysis');
</script>

{@debug data}
<div class="bg-white shadow flex overflow-x-auto">
	<div class="w-full h-screen">
		<GraphExplorer title="Visual Analysis" data={data.data.graph} edgeLength={100} />
	</div>
</div>
