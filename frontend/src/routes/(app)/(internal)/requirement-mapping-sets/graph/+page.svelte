<script lang="ts">
	import type { PageData } from './$types';
	import GraphExplorer from '$lib/components/DataViz/GraphExplorer.svelte';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="bg-white shadow-sm flex overflow-x-auto">
	<div class="w-full h-screen">
		<GraphExplorer
			title="Mapping Explorer"
			data={data.data}
			color={['#5470c6', '#9ca3af']}
			showNodeLabels
		/>
	</div>
</div>
