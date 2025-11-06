<script lang="ts">
	import type { PageData } from './$types';
	import GraphExplorer from '$lib/components/DataViz/GraphExplorer.svelte';
	import { goto } from '$lib/utils/breadcrumbs';
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
			onNodeDoubleClick={(params) => {
				if (params.dataType === 'node') {
					console.log(params.data);
					goto(`/stored-libraries/${params.data?.pk}`, {
						breadcrumbAction: 'push',
						label: params.data?.name || 'Detail'
					});
				}
			}}
			showNodeLabels
		/>
	</div>
</div>
