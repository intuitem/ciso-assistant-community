<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	export let data: PageData;
	import LineHeatmap from '$lib/components/DataViz/LineHeatmap.svelte';
	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { page } from '$app/stores';
</script>

<DetailView {data}>
	<div slot="actions" class="flex flex-col space-y-2">
		<Anchor
			href={`${$page.url.pathname}/visual`}
			class="btn variant-filled-primary h-fit"
			breadcrumbAction="push"><i class="fa-solid fa-heart-pulse mr-2" />{m.visualAnalysis()}</Anchor
		>
	</div>
	<div slot="widgets" class="h-full flex flex-col space-y-4">
		<div class="bg-gray-50">
			{#each data.metrics as aa}
				<div>{aa.asset}</div>
				<LineHeatmap data={aa.metrics} />
			{/each}
		</div>
	</div>
</DetailView>
