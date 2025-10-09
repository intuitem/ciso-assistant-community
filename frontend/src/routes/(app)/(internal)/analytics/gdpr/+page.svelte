<script lang="ts">
	import WorldMap from '$lib/components/DataViz/WorldMap.svelte';
	import TreemapChart from '$lib/components/Chart/TreemapChart.svelte';
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import { m } from '$paraglide/messages';
	import Card from './Card.svelte';
	import type { PageData } from './$types';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="grid grid-cols-12">
	<div class="grid grid-cols-5 bg-slate-100 p-4 gap-4 col-span-12">
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
		<Card
			icon="fa-solid fa-user-shield"
			text={m.openRightRequests()}
			count={data.data.open_right_requests_count}
		/>
		<Card
			icon="fa-solid fa-triangle-exclamation"
			text={m.openDataBreaches()}
			count={data.data.open_data_breaches_count}
		/>
	</div>
	<div class="col-span-7 flex items-center justify-center p-4">
		{#if data?.data?.countries?.length > 0}
			<WorldMap data={data.data.countries} />
		{:else}
			<div class="text-slate-700">{m.noDataAvailable()}</div>
		{/if}
	</div>
	<div class="col-span-5 min-h-96">
		<TreemapChart tree={data.data.pd_categories} name="pd_cat" translate={true} />
	</div>
	<div class="col-span-6 p-4">
		<DonutChart
			name="breach_types"
			title={m.dataBreachesByType()}
			values={data.data.breach_types || []}
			height="h-96"
		/>
	</div>
	<div class="col-span-6 p-4">
		<DonutChart
			name="request_types"
			title={m.rightRequestsByType()}
			values={data.data.request_types || []}
			height="h-96"
		/>
	</div>
</div>
