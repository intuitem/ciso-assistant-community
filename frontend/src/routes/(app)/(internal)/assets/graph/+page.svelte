<script lang="ts">
	import type { PageData } from './$types';
	import GraphExplorer from '$lib/components/DataViz/GraphExplorer.svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	pageTitle.set('Assets Explorer');
</script>

<div class="bg-white shadow-sm flex flex-col overflow-x-auto">
	<div class="flex justify-end items-center p-2 border-b border-gray-200">
		{#if data.hideDomains}
			<a
				href="/assets/graph"
				data-sveltekit-reload
				class="text-primary-800 hover:text-primary-500 cursor-pointer text-sm"
			>
				<i class="fa-solid fa-eye mr-1"></i>
				{m.showDomains()}
			</a>
		{:else}
			<a
				href="/assets/graph?hideDomains=true"
				data-sveltekit-reload
				class="text-primary-800 hover:text-primary-500 cursor-pointer text-sm"
			>
				<i class="fa-solid fa-eye-slash mr-1"></i>
				{m.hideDomains()}
			</a>
		{/if}
	</div>
	<div class="w-full h-screen">
		<GraphExplorer title="Assets Explorer" data={data.data} edgeLength={100} maxLegendItems={15} />
	</div>
</div>
