<script lang="ts">
	import type { PageData } from './$types';
	import GraphExplorer from '$lib/components/DataViz/GraphExplorer.svelte';
	import { pageTitle } from '$lib/utils/stores';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	pageTitle.set(data.data.meta.display_name);
</script>

<div class="bg-white shadow flex overflow-x-auto">
	<div class="w-full h-screen">
		<GraphExplorer title="Mapping Explorer" data={data.data} />
	</div>
</div>
