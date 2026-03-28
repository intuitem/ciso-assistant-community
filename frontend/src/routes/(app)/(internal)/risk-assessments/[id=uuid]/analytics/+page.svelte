<script lang="ts">
	import RadarChart from '$lib/components/Chart/RadarChart.svelte';
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import BarChart from '$lib/components/Chart/BarChart.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';

	let { data } = $props();

	const treatmentColors: Record<string, string> = {
		open: '#94a3b8',
		mitigate: '#3b82f6',
		accept: '#22c55e',
		avoid: '#f59e0b',
		transfer: '#a855f7'
	};

	// SOK labels come as "low", "medium", "high" — sorted by level ascending
	const sokColors: Record<string, string> = {
		low: '#f87171',
		medium: '#fbbf24',
		high: '#34d399'
	};
</script>

<div class="space-y-6 p-6">
	<!-- Header -->
	<div class="flex items-center gap-4">
		<Anchor
			href="/risk-assessments/{data.risk_assessment.id}"
			breadcrumbAction="pop"
			class="flex items-center justify-center w-9 h-9 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors text-gray-600"
		>
			<i class="fa-solid fa-arrow-left text-sm"></i>
		</Anchor>
		<div>
			<h1 class="text-xl font-bold text-gray-900">{m.analytics()}</h1>
			<p class="text-sm text-gray-500">{data.risk_assessment.name} - {data.risk_assessment.version}</p>
		</div>
	</div>

	{#await data.stream.analytics}
		<div class="flex items-center justify-center py-20">
			<LoadingSpinner />
		</div>
	{:then analytics}
		<!-- Row 1: Threat Radar + Treatment Distribution -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
			<!-- Threat Radar / Bar -->
			<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
				<h3 class="text-lg font-semibold text-gray-900 mb-2">{safeTranslate('threatsBreakdown')}</h3>
				{#if analytics.threats?.labels?.length > 0}
					{#if analytics.threats.labels.length <= 10}
						<div class="h-80">
							<RadarChart
								name="threatRadar"
								labels={analytics.threats.labels}
								values={analytics.threats.values}
							/>
						</div>
					{:else}
						{@const threatLabels = [...analytics.threats.labels].reverse().map((l) => safeTranslate(l.name))}
					{@const threatValues = [...analytics.threats.values].reverse()}
						<div class="overflow-y-auto max-h-80">
							<div style="height: {Math.max(224, threatLabels.length * 28)}px">
								<BarChart
									name="threatBar"
									labels={threatLabels}
									values={threatValues}
									horizontal={true}
								/>
							</div>
						</div>
					{/if}
				{:else}
					<div class="h-80 flex items-center justify-center text-gray-500">
						<p>{m.noThreatsMapped()}</p>
					</div>
				{/if}
			</div>

			<!-- Treatment Distribution -->
			<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
				<h3 class="text-lg font-semibold text-gray-900 mb-2">{safeTranslate('treatmentDistribution')}</h3>
				{#if analytics.treatment?.labels?.length > 0}
					{@const treatmentValues = analytics.treatment.labels.map((label, i) => ({
						name: label,
						value: analytics.treatment.values[i]
					}))}
					<div class="h-80">
						<DonutChart
							name="treatmentDonut"
							values={treatmentValues}
							colors={treatmentValues.map((t) => treatmentColors[t.name] ?? '#6b7280')}
						/>
					</div>
				{:else}
					<div class="h-80 flex items-center justify-center text-gray-500">
						<p>{m.noDataAvailable()}</p>
					</div>
				{/if}
			</div>
		</div>

		<!-- Row 2: Strength of Knowledge + Assets at Risk -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
			<!-- Strength of Knowledge -->
			<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
				<h3 class="text-lg font-semibold text-gray-900 mb-2">{m.strengthOfKnowledge()}</h3>
				{#if analytics.strength_of_knowledge?.labels?.length > 0}
					{@const sokValues = analytics.strength_of_knowledge.labels.map((label, i) => ({
						name: label,
						value: analytics.strength_of_knowledge.values[i]
					}))}
					<div class="h-80">
						<DonutChart
							name="sokDonut"
							values={sokValues}
							colors={sokValues.map((s) => sokColors[s.name] ?? '#6b7280')}
						/>
					</div>
				{:else}
					<div class="h-80 flex items-center justify-center text-gray-500">
						<p>{m.noDataAvailable()}</p>
					</div>
				{/if}
			</div>

			<!-- Assets at Risk -->
			<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
				<h3 class="text-lg font-semibold text-gray-900 mb-2">{safeTranslate('assetsAtRisk')}</h3>
				{#if analytics.assets?.labels?.length > 0}
					<div class="h-80">
						<BarChart
							name="assetsBar"
							labels={[...analytics.assets.labels].reverse()}
							values={[...analytics.assets.values].reverse()}
							horizontal={true}
						/>
					</div>
				{:else}
					<div class="h-80 flex items-center justify-center text-gray-500">
						<p>{m.noDataAvailable()}</p>
					</div>
				{/if}
			</div>
		</div>

	{:catch}
		<div class="text-red-500 text-center py-12">
			<p>{m.anErrorOccurred()}</p>
		</div>
	{/await}
</div>
