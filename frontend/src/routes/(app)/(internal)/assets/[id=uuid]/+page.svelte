<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '#lib/components/DetailView/DetailView.svelte';
	import ObjectivesComparisonTable from '#lib/components/Assets/ObjectivesComparisonTable.svelte';
	import HomologationTab from '#lib/components/Assets/HomologationTab.svelte';
	import { m } from '#paraglide/messages.js';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const journey = $derived(data.journey);
	// Same switches as the Accreditations menu entry.
	const accreditationsOn = $derived(
		Boolean(data.featureflags?.project_management && (data.featureflags?.accreditations ?? true))
	);
	const extraTabs = $derived(
		accreditationsOn &&
			journey &&
			(data.canFrame || journey.response || journey.accreditation || journey.past_cycles?.length)
			? [{ value: 'homologation', label: m.accreditation(), content: homologation }]
			: []
	);
</script>

{#snippet homologation()}
	<HomologationTab {journey} assetId={data.data.id} />
{/snippet}

<DetailView {data} {extraTabs}>
	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4">
			<div class="card p-4 bg-surface-50-950 shadow-xs grow">
				<ObjectivesComparisonTable
					comparisons={data.data.security_objectives_comparison}
					title={m.securityObjectives()}
					icon="fa-shield-halved"
				/>

				<ObjectivesComparisonTable
					comparisons={data.data.recovery_objectives_comparison}
					title={m.recoveryIndicators()}
					icon="fa-bullseye"
					uppercaseLabels={true}
				/>
			</div>
		</div>
	{/snippet}
</DetailView>
