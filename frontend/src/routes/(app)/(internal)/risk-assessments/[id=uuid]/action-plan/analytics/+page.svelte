<script lang="ts">
	import AppliedControlsAnalytics from '$lib/components/DataViz/AppliedControlsAnalytics.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="p-4 space-y-4">
	<div class="flex items-center gap-3">
		<Anchor
			href={`/risk-assessments/${data.risk_assessment.id}/action-plan`}
			class="btn variant-ghost-surface"
		>
			<i class="fa-solid fa-arrow-left mr-2" aria-hidden="true"></i>{m.actionPlan()}
		</Anchor>
		<div>
			<h1 class="text-2xl font-bold text-surface-900-100">{m.appliedControlsAnalytics()}</h1>
			<p class="text-sm text-surface-600-400">
				{data.risk_assessment.name}
				{#if data.risk_assessment.version}
					- {data.risk_assessment.version}
				{/if}
			</p>
		</div>
	</div>

	<AppliedControlsAnalytics analyticsData={data.analytics} />
</div>
