<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import ObjectivesComparisonTable from '$lib/components/Assets/ObjectivesComparisonTable.svelte';
	import { m } from '$paraglide/messages';

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
