<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	export let data: PageData;
	import LineHeatmap from '$lib/components/DataViz/LineHeatmap.svelte';
	import { m } from '$paraglide/messages';
</script>

<DetailView {data}>
	<div slot="widgets" class="h-full flex flex-col space-y-4">
		<div class="bg-gray-50">
			{#each data.metrics as aa}
				<div>{aa.asset}</div>
				<LineHeatmap data={aa.metrics} />
			{/each}
		</div>
	</div>
</DetailView>
