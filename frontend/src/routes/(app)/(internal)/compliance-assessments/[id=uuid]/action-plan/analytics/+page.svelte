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
			href={`/compliance-assessments/${data.compliance_assessment.id}/action-plan`}
			class="btn variant-ghost-surface"
		>
			<i class="fa-solid fa-arrow-left mr-2" aria-hidden="true"></i>{m.actionPlan()}
		</Anchor>
		<div>
			<h1 class="text-2xl font-bold text-gray-900">{m.appliedControlsAnalytics()}</h1>
			<p class="text-sm text-gray-500">
				{data.compliance_assessment.name}
				{#if data.compliance_assessment.version}
					- {data.compliance_assessment.version}
				{/if}
			</p>
		</div>
	</div>

	<AppliedControlsAnalytics analyticsData={data.analytics} />
</div>
