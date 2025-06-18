<script lang="ts">
	import type { PageData } from './$types';
	import GraphExplorer from '$lib/components/DataViz/GraphExplorer.svelte';
	import { pageTitle } from '$lib/utils/stores';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="bg-white shadow flex overflow-x-auto">
	<div class="w-full h-screen">
		<GraphExplorer title="Mapping Explorer" initLayout="circular" data={data.data} />
	</div>
</div>
