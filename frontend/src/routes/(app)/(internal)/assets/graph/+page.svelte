<script lang="ts">
	import type { PageData } from './$types';
	import GraphExplorer from '$lib/components/DataViz/GraphExplorer.svelte';
	import { pageTitle } from '$lib/utils/stores';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	pageTitle.set('Assets Explorer');
</script>

<div class="bg-white shadow flex overflow-x-auto">
	<div class="w-full h-screen">
		<GraphExplorer title="Assets Explorer" data={data.data} edgeLength={100} />
	</div>
</div>
