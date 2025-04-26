<script lang="ts">
	import WorldMap from '$lib/components/DataViz/WorldMap.svelte';
	import TreemapChart from '$lib/components/Chart/TreemapChart.svelte';
	import { m } from '$paraglide/messages';
	import Card from './Card.svelte';
	import type { PageData } from './$types';
	export let data: PageData;
</script>

<div class="grid grid-cols-12">
	<div class="grid grid-cols-4 bg-slate-100 p-4 gap-4 col-span-12">
		<Card
			icon="fa-solid fa-gem"
			text={m.personalDataCategoriesIdentified()}
			count={data.data.pd_cat_count}
		/>
		<Card
			icon="fa-solid fa-file-lines"
			text={m.documentedProcessings()}
			count={data.data.processings_count}
		/>
		<Card
			icon="fa-solid fa-user-tie"
			text={m.dataRecipients()}
			count={data.data.recipients_count}
		/>
		<!-- <Card icon="fa-solid fa-circle-exclamation" text="Incidents" count={2} /> -->
	</div>
	<div class="col-span-7">
		{#if data?.data?.countries?.length > 0}
			<WorldMap data={data.data.countries} />
		{:else}
			<div class="h-12 flex items-center justify-center text-slate-700">{m.noDataAvailable()}</div>
		{/if}
	</div>
	<div class="col-span-5">
		<TreemapChart tree={data.data.pd_categories} name="pd_cat" />
	</div>
</div>
