<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import LineHeatmap from '$lib/components/DataViz/LineHeatmap.svelte';
	import ObjectivesComparisonTable from '$lib/components/Assets/ObjectivesComparisonTable.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<DetailView {data}>
	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4">
			<div class="card p-4 bg-gray-50 shadow-xs grow">
				<ObjectivesComparisonTable
					comparisons={data.asset.security_objectives_comparison}
					title={m.securityObjectives()}
					icon="fa-shield-halved"
				/>

				<ObjectivesComparisonTable
					comparisons={data.asset.recovery_objectives_comparison}
					title={m.recoveryIndicators()}
					icon="fa-bullseye"
					uppercaseLabels={true}
				/>

				<!-- Impact Over Time -->
				<div class="font-serif font-bold mb-2">
					<i class="fa-solid fa-chart-line mr-2"></i>{m.impactOverTime()}
				</div>
				<LineHeatmap data={data.aaMetrics} />
			</div>
		</div>
	{/snippet}
	{#snippet actions()}
		<Anchor
			breadcrumbAction="push"
			href={`${page.url.pathname}/dependencies`}
			class="btn preset-filled-secondary-500 h-fit"
		>
			<i class="fa-solid fa-sitemap mr-2"></i>
			{m.assetDependencies()}
		</Anchor>
	{/snippet}
</DetailView>
