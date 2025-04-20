<script lang="ts">
	import Card from '$lib/components/DataViz/Card.svelte';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';
	export let data: PageData;
	import LoadingSpinner from '$lib/components/utils/LoadingSpinner.svelte';
	import StackedBarsNormalized from '$lib/components/Chart/StackedBarsNormalized.svelte';
	import HalfDonutChart from '$lib/components/Chart/HalfDonutChart.svelte';
	import NightingaleChart from '$lib/components/Chart/NightingaleChart.svelte';
	import RadarChart from '$lib/components/Chart/RadarChart.svelte';
	$: totalRisksCount = data.risks_count_per_level.current.reduce(
		(sum, level) => sum + level.value,
		0
	);

	// Reactive boolean that checks if there are any risks (sum > 0)
	$: hasRisks = totalRisksCount > 0;
</script>

{@debug data}
<main class="bg-white p-2">
	{#await data.stream.metrics}
		<div class="col-span-3 lg:col-span-1">
			<div>Refreshing data ..</div>
			<LoadingSpinner />
		</div>
	{:then metrics}
		<div class="grid grid-cols-4 p-2 gap-2">
			<!---->
			<fieldset
				class="fieldset col-span-full border-slate-300 border rounded-lg grid grid-cols-6 gap-2 p-2 bg-gradient-to-b from-slate-50 to-white"
			>
				<legend class="m-2 text-lg font-bold capitalize font-serif"
					><i class="fa-solid fa-shield-halved m-2"></i>{m.appliedControls()}</legend
				>
				<Card count={metrics.controls.total} label={m.sumpageTotal()} />
				<Card count={metrics.controls.active} label={m.sumpageActive()} />
				<Card count={metrics.controls.deprecated} label={m.sumpageDeprecated()} emphasis={true} />
				<div class="col-span-3 row-span-3 bg-white shadow">
					<NightingaleChart name="nightingale" values={metrics.csf_functions} />
				</div>
				<Card count={metrics.controls.to_do} label={m.sumpageToDo()} />
				<Card count={metrics.controls.in_progress} label={m.sumpageInProgress()} />
				<Card count={metrics.controls.on_hold} label={m.sumpageOnHold()} emphasis={true} />
				<Card count={metrics.controls.p1} label={m.sumpageP1()} emphasis={true} />
				<Card count={metrics.controls.eta_missed} label={m.sumpageEtaMissed()} emphasis={true} />
			</fieldset>
			<!---->
			<fieldset
				class="fieldset col-span-full border-slate-300 border rounded-lg grid grid-cols-6 gap-2 p-2 bg-gradient-to-b from-slate-50 to-white"
			>
				<legend class="m-2 text-lg font-bold capitalize font-serif"
					><i class="fa-solid fa-list-check m-2"></i>{m.compliance()}</legend
				>
				<div class="col-span-5 row-span-3">
					<StackedBarsNormalized
						names={metrics.audits_stats.names}
						data={metrics.audits_stats.data}
						uuids={metrics.audits_stats.uuids}
					/>
				</div>
				<Card count="{metrics.compliance.progress_avg}%" label={m.sumpageAvgProgress()} />
				<Card
					count={metrics.compliance.non_compliant_items}
					label={m.sumpageNonCompliantItems()}
					emphasis={true}
				/>
				<Card count={metrics.compliance.evidences} label={m.sumpageEvidences()} />
			</fieldset>
			<!---->
			<fieldset
				class="fieldset col-span-full bg-slate-50 border-slate-300 border rounded-lg grid grid-cols-6 gap-2 p-2 bg-slate-50"
			>
				<legend class="m-2 text-lg font-bold capitalize font-serif"
					><i class="fa-solid fa-biohazard m-2"></i>{m.risk()}</legend
				>
				<div class="col-span-2 row-span-2 bg-white shadow">
					{#if data.threats_count.results.labels.length > 0}
						<RadarChart
							name="threatRadar"
							title={m.threatRadarChart()}
							labels={data.threats_count.results.labels}
							values={data.threats_count.results.values}
						/>
					{:else}
						<div class="py-4 flex items-center justify-center">
							<p class="">{m.noThreatsMapped()}</p>
						</div>
					{/if}
				</div>
				<div class="col-span-2 row-span-2 h-80 bg-white shadow">
					{#if hasRisks}
						<HalfDonutChart
							name="current_h"
							title={m.sumpageTitleCurrentRisks()}
							values={data.risks_count_per_level.current}
							colors={data.risks_count_per_level.current.map((object) => object.color)}
						/>
					{:else}
						<p>{m.noDataAvailable()}</p>
					{/if}
				</div>
				<div class="col-span-2 row-span-2 h-80 bg-white shadow">
					{#if hasRisks}
						<HalfDonutChart
							name="residual_h"
							title={m.sumpageTitleResidualRisks()}
							values={data.risks_count_per_level.residual}
							colors={data.risks_count_per_level.residual.map((object) => object.color)}
						/>
					{:else}
						<p>{m.noDataAvailable()}</p>
					{/if}
				</div>
				<div></div>
				<Card count={metrics.risk.assessments} label={m.sumpageAssessments()} />
				<Card count={metrics.risk.scenarios} label={m.sumpageScenarios()} />
				<Card count={metrics.risk.threats} label={m.sumpageMappedThreats()} />
				<Card count={metrics.risk.acceptances} label={m.sumpageRiskAccepted()} />
			</fieldset>
			<!---->
		</div>
	{:catch error}
		<div class="col-span-3 lg:col-span-1">
			<p class="text-red-500">Error loading metrics</p>
		</div>
	{/await}
</main>
<!---->
