<script lang="ts">
	import type { PageData } from './$types';
	import GraphExplorer from '$lib/components/DataViz/GraphExplorer.svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	pageTitle.set('Visual Analysis');
	const color = [
		'#91cc75',
		'#fac858',
		'#e63946',
		'#ea7ccc',
		'#13B8A6',
		'#fc8452',
		'#ff006e',
		'#3a86ff',
		'#3d348b',
		'#9a60b4'
	];
	const zoom = 1.5;
</script>

<div class="flex items-center justify-between mb-4">
	<Anchor
		breadcrumbAction="push"
		href={`/ebios-rm/${page.params.id}`}
		class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
	>
		<i class="fa-solid fa-arrow-left"></i>
		<p>{m.goBackToEbiosRmStudy()}</p>
	</Anchor>
</div>

<div class="bg-white shadow-sm flex overflow-x-auto">
	<div class="w-full h-screen">
		<GraphExplorer
			title="Visual Analysis (beta)"
			data={data.data.graph}
			edgeLength={150}
			{color}
			{zoom}
		/>
	</div>
</div>
