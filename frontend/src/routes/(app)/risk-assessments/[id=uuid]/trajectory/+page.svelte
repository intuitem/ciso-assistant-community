<script lang="ts">
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import RiskTrajectoryMatrix from '$lib/components/RiskMatrix/RiskTrajectoryMatrix.svelte';
	import type { Stage } from '$lib/components/RiskMatrix/trajectory';
	import { m } from '$paraglide/messages';

	let { data } = $props();

	let stages: Stage[] = $derived(
		page.data?.featureflags?.inherent_risk
			? ['inherent', 'current', 'residual']
			: ['current', 'residual']
	);
</script>

<div class="space-y-6 p-6">
	<div class="flex items-center gap-4">
		<Anchor
			href="/risk-assessments/{data.risk_assessment.id}"
			breadcrumbAction="pop"
			class="flex items-center justify-center w-9 h-9 rounded-lg bg-surface-100-900 hover:bg-surface-200-800 transition-colors text-surface-600-400"
		>
			<i class="fa-solid fa-arrow-left text-sm"></i>
		</Anchor>
		<div>
			<h1 class="text-xl font-bold text-surface-900-100">{m.riskTrajectory()}</h1>
			<p class="text-sm text-surface-600-400">
				{data.risk_assessment.name} - {data.risk_assessment.version}
			</p>
		</div>
	</div>

	<section class="rounded-xl border border-surface-200-800 bg-surface-50-950 p-6">
		<RiskTrajectoryMatrix
			riskMatrix={data.risk_assessment.risk_matrix}
			scenarios={data.risk_assessment.risk_scenarios}
			controls={data.controls}
			controlsError={data.controlsError}
			{stages}
		/>
	</section>
</div>
