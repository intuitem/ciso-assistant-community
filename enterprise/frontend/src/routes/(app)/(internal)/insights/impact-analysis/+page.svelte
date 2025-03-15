<script lang="ts">
	import type { PageData } from './$types';
	export let data: PageData;
	import GraphExplorer from '$lib/components/DataViz/GraphExplorer.svelte';
	import { pageTitle } from '$lib/utils/stores';
</script>

<div class="bg-white shadow flex overflow-x-auto">
	<div class="w-full h-screen">
		<GraphExplorer title="Mapping Explorer" initLayout="circular" data={data.data} />
	</div>
</div>
