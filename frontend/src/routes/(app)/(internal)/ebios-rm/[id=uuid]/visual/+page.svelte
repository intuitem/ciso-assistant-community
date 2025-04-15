<script lang="ts">
	import type { PageData } from './$types';
	export let data: PageData;
	import GraphExplorer from '$lib/components/DataViz/GraphExplorer.svelte';
	import { pageTitle } from '$lib/utils/stores';
	pageTitle.set('Visual Analysis');
	const color = ['#fc8452', '#ea7ccc', '#fac858', '#91cc75'];
</script>

<div class="bg-white shadow flex overflow-x-auto">
	<div class="w-full h-screen">
		<GraphExplorer title="Visual Analysis" data={data.data.graph} edgeLength={150} {color} />
	</div>
</div>
