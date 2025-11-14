<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import RiskMatrix from '$lib/components/RiskMatrix/RiskMatrix.svelte';
	import RiskScenarioItem from '$lib/components/RiskMatrix/RiskScenarioItem.svelte';
	import EcosystemCircularRadarChart from '$lib/components/Chart/EcosystemCircularRadarChart.svelte';
	import GraphComponent from '../../../operating-modes/[id=uuid]/graph/OperatingModeGraph.svelte';
	import type { PageData } from './$types';
	import type { RiskMatrixJsonDefinition, RiskScenario } from '$lib/utils/types';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';

	interface Props {
		data: PageData;
	}

	$effect(() => {
		// Ensure page title includes "print" class when printing
		const mediaQueryList = window.matchMedia('print');
		const handlePrint = () => {
			document.documentElement.classList.add('is-printing');
		};
		const handleAfterPrint = () => {
			document.documentElement.classList.remove('is-printing');
		};
		window.addEventListener('beforeprint', handlePrint);
		window.addEventListener('afterprint', handleAfterPrint);

		return () => {
			window.removeEventListener('beforeprint', handlePrint);
			window.removeEventListener('afterprint', handleAfterPrint);
		};
	});

	let { data }: Props = $props();
	pageTitle.set('EBIOS RM Study Report');

	const { reportData } = data;
	const study = reportData.study;
	const useBubbles = data.useBubbles;
	const inherentRiskEnabled = data.inherentRiskEnabled;

	const pertinenceColor: Record<string, string> = {
		undefined: 'bg-gray-200 text-gray-700',
		irrelevant: 'bg-green-200 text-green-700',
		partially_relevant: 'bg-yellow-200 text-yellow-700',
		fairly_relevant: 'bg-orange-200 text-orange-700',
		highly_relevant: 'bg-red-200 text-red-700'
	};

	function exportPDF() {
		window.print();
	}

	// Build risk cluster for current risk level
	const buildRiskCluster = (
		scenarios: RiskScenario[],
		risk_matrix: any,
		risk: 'current' | 'residual' | 'inherent'
	) => {
		const parsedRiskMatrix: RiskMatrixJsonDefinition =
			typeof risk_matrix.json_definition === 'string'
				? JSON.parse(risk_matrix.json_definition)
				: (risk_matrix.json_definition as RiskMatrixJsonDefinition);
		const grid: unknown[][][] = Array.from({ length: parsedRiskMatrix.probability.length }, () =>
			Array.from({ length: parsedRiskMatrix.impact.length }, () => [])
		);
		scenarios.forEach((scenario: RiskScenario) => {
			const probabilityData = scenario[`${risk}_proba`];
			const impactData = scenario[`${risk}_impact`];
			const probability = probabilityData?.value ?? -1;
			const impact = impactData?.value ?? -1;
			probability >= 0 && impact >= 0 ? grid[probability][impact].push(scenario) : undefined;
		});
		return grid;
	};
</script>

<div class="bg-white shadow-sm p-4 px-8 max-w-5xl mx-auto relative">
	<!-- Workshop Navigation Pad -->
	<div
		class="fixed top-24 right-8 z-10 bg-white border-2 border-gray-300 rounded-lg shadow-lg p-3 no-print"
	>
		<div class="text-xs font-semibold text-gray-600 mb-2 text-center">{m.workshops()}</div>
		<div class="flex flex-col gap-2 items-center">
			<a
				href="#workshop-1"
				class="w-10 h-10 flex items-center justify-center rounded-lg bg-pink-600 hover:bg-pink-700 text-white font-bold transition-colors"
				title="{m.workshop()} 1"
			>
				1
			</a>
			<a
				href="#workshop-2"
				class="w-10 h-10 flex items-center justify-center rounded-lg bg-fuchsia-900 hover:bg-fuchsia-950 text-white font-bold transition-colors"
				title="{m.workshop()} 2"
			>
				2
			</a>
			<a
				href="#workshop-3"
				class="w-10 h-10 flex items-center justify-center rounded-lg bg-teal-500 hover:bg-teal-600 text-white font-bold transition-colors"
				title="{m.workshop()} 3"
			>
				3
			</a>
			<a
				href="#workshop-4"
				class="w-10 h-10 flex items-center justify-center rounded-lg bg-yellow-600 hover:bg-yellow-700 text-white font-bold transition-colors"
				title="{m.workshop()} 4"
			>
				4
			</a>
			<a
				href="#workshop-5"
				class="w-10 h-10 flex items-center justify-center rounded-lg bg-red-500 hover:bg-red-600 text-white font-bold transition-colors"
				title="{m.workshop()} 5"
			>
				5
			</a>
		</div>
	</div>

	<!-- Back to Study Link and Export Button -->
	<div class="mb-4 flex justify-between items-center no-print">
		<Anchor
			breadcrumbAction="push"
			href={`/ebios-rm/${study.id}`}
			class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
		>
			<i class="fa-solid fa-arrow-left"></i>
			<p>{m.backToStudy()}</p>
		</Anchor>
		<button
			onclick={exportPDF}
			class="btn preset-filled-primary-500 flex items-center gap-2 no-print"
		>
			<i class="fa-solid fa-file-pdf"></i>
			<span>{m.exportPdf()}</span>
		</button>
	</div>

	<!-- Study Header -->
	<div class="mb-6">
		<h1 class="text-3xl font-bold text-gray-900 mb-2">{study.name}</h1>
		{#if study.description}
			<div class="text-gray-600 mb-4">
				<MarkdownRenderer content={study.description} />
			</div>
		{/if}
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
			<div>
				<span class="font-semibold text-gray-700">{m.version()}:</span>
				<span class="ml-2">{study.version || 'N/A'}</span>
			</div>
			<div>
				<span class="font-semibold text-gray-700">{m.status()}:</span>
				<span class="ml-2">{study.status ? safeTranslate(study.status) : 'N/A'}</span>
			</div>
		</div>
	</div>

	<!-- Workshop 1 -->
	<div id="workshop-1" class="my-12 scroll-mt-20 workshop-divider">
		<hr class="border-t-4 border-pink-600" />
		<div class="text-center -mt-5 mb-12">
			<span class="bg-white px-6 py-2 text-xl font-bold text-pink-600">
				{m.workshop()} 1 - {m.frameTheStudy()}
			</span>
		</div>
	</div>

	<!-- Selected Assets -->
	<section class="mb-6">
		<!-- Selected Assets -->
		{#if study.assets && study.assets.length > 0}
			<div class="mb-4">
				<h3 class="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
					<i class="fa-solid fa-server"></i>
					{m.assets()}
					<span class="badge preset-tonal-secondary text-xs">{study.assets.length}</span>
				</h3>
				<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
					{#each study.assets as asset}
						<div
							class="border border-gray-200 rounded-lg p-3 bg-gray-50 hover:shadow-md transition-shadow"
						>
							<div class="flex items-start gap-2">
								{#if asset.type === 'PR'}
									<i class="fa-solid fa-briefcase text-blue-500 mt-1"></i>
								{:else}
									<i class="fa-solid fa-cube text-blue-500 mt-1"></i>
								{/if}
								<div class="flex-1">
									<div class="font-semibold text-gray-900">{asset.str}</div>
									{#if asset.folder}
										<div class="text-xs text-gray-600">
											<span class="font-medium">{m.domain()}:</span>
											<span class="ml-1">{asset.folder.str}</span>
										</div>
									{/if}
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Observation -->
		{#if study.observation}
			<div class="mb-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
				<h3 class="text-lg font-semibold text-gray-800 mb-2 flex items-center gap-2">
					<i class="fa-solid fa-eye text-gray-500"></i>
					<span>{m.observation()}</span>
				</h3>
				<div class="text-gray-600">
					<MarkdownRenderer content={study.observation} />
				</div>
			</div>
		{/if}
	</section>

	<!-- Feared Events Section -->
	{#if reportData.feared_events.length > 0}
		<section class="mb-6 page-break-section">
			<h2
				class="text-lg font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2 flex items-center gap-2"
			>
				{m.fearedEvents()}
				<span class="badge preset-tonal-secondary text-xs">{reportData.feared_events.length}</span>
			</h2>
			<div class="space-y-4">
				{#each reportData.feared_events as event}
					<div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
						<h3 class="text-lg font-semibold text-gray-800 mb-2">{event.name}</h3>
						<div class="flex flex-wrap gap-4 text-sm mb-3">
							<div>
								<span class="font-semibold text-gray-700">{m.gravity()}:</span>
								<span
									class="ml-2 px-2 py-1 rounded"
									style="background-color: {event.gravity.hexcolor}"
								>
									{safeTranslate(event.gravity.name)}
								</span>
							</div>
							{#if event.assets.length > 0}
								<div>
									<span class="font-semibold text-gray-700">{m.assets()}:</span>
									<span class="ml-2">{event.assets.map((a) => a.str).join(', ')}</span>
								</div>
							{/if}
							{#if event.qualifications.length > 0}
								<div>
									<span class="font-semibold text-gray-700">{m.qualifications()}:</span>
									<span class="ml-2"
										>{event.qualifications.map((q) => safeTranslate(q.str)).join(', ')}</span
									>
								</div>
							{/if}
						</div>
						{#if event.description}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.description()}:</span>
								<p class="mt-1 text-gray-600">{event.description}</p>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Compliance Assessments Section -->
	{#if reportData.compliance_assessments && reportData.compliance_assessments.length > 0}
		<section class="mb-6 page-break-section">
			<h2
				class="text-lg font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2 flex items-center gap-2"
			>
				{m.complianceAssessments()}
				<span class="badge preset-tonal-secondary text-xs"
					>{reportData.compliance_assessments.length}</span
				>
			</h2>
			<div class="space-y-4">
				{#each reportData.compliance_assessments as assessment}
					<div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
						<div class="flex justify-between items-start mb-2">
							<div>
								<h3 class="text-lg font-semibold text-gray-800">{assessment.name}</h3>
								{#if assessment.framework}
									<p class="text-sm text-gray-600">{assessment.framework}</p>
								{/if}
							</div>
							{#if assessment.version}
								<span class="badge bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
									v{assessment.version}
								</span>
							{/if}
						</div>

						<!-- Progress Bar -->
						{#if assessment.progress !== undefined}
							<div class="mb-3">
								<div class="flex justify-between items-center mb-1">
									<span class="text-sm font-semibold text-gray-700">{m.progress()}:</span>
									<span class="text-sm font-semibold text-gray-900">{assessment.progress}%</span>
								</div>
								<div class="w-full bg-gray-200 rounded-full h-2.5">
									<div
										class="h-2.5 rounded-full transition-all duration-300"
										class:bg-red-500={assessment.progress < 25}
										class:bg-orange-500={assessment.progress >= 25 && assessment.progress < 50}
										class:bg-yellow-500={assessment.progress >= 50 && assessment.progress < 75}
										class:bg-green-500={assessment.progress >= 75}
										style="width: {assessment.progress}%"
									></div>
								</div>
							</div>
						{/if}

						<!-- Result Counts -->
						{#if assessment.result_counts}
							<div class="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3">
								{#if assessment.result_counts.compliant !== undefined}
									<div class="bg-green-50 border border-green-200 rounded p-2 text-center">
										<div class="text-2xl font-bold text-green-700">
											{assessment.result_counts.compliant}
										</div>
										<div class="text-xs text-green-600">{safeTranslate('compliant')}</div>
									</div>
								{/if}
								{#if assessment.result_counts.partially_compliant !== undefined}
									<div class="bg-yellow-50 border border-yellow-200 rounded p-2 text-center">
										<div class="text-2xl font-bold text-yellow-700">
											{assessment.result_counts.partially_compliant}
										</div>
										<div class="text-xs text-yellow-600">
											{safeTranslate('partiallyCompliant')}
										</div>
									</div>
								{/if}
								{#if assessment.result_counts.non_compliant !== undefined}
									<div class="bg-red-50 border border-red-200 rounded p-2 text-center">
										<div class="text-2xl font-bold text-red-700">
											{assessment.result_counts.non_compliant}
										</div>
										<div class="text-xs text-red-600">{safeTranslate('nonCompliant')}</div>
									</div>
								{/if}
								{#if assessment.result_counts.not_applicable !== undefined}
									<div class="bg-gray-50 border border-gray-200 rounded p-2 text-center">
										<div class="text-2xl font-bold text-gray-700">
											{assessment.result_counts.not_applicable}
										</div>
										<div class="text-xs text-gray-600">{safeTranslate('notApplicable')}</div>
									</div>
								{/if}
								{#if assessment.result_counts.not_assessed !== undefined}
									<div class="bg-blue-50 border border-blue-200 rounded p-2 text-center">
										<div class="text-2xl font-bold text-blue-700">
											{assessment.result_counts.not_assessed}
										</div>
										<div class="text-xs text-blue-600">{safeTranslate('notAssessed')}</div>
									</div>
								{/if}
							</div>
						{/if}

						<div class="flex flex-wrap gap-4 text-sm">
							{#if assessment.eta}
								<div>
									<span class="font-semibold text-gray-700">{m.eta()}:</span>
									<span class="ml-2">{formatDateOrDateTime(assessment.eta)}</span>
								</div>
							{/if}
							{#if assessment.due_date}
								<div>
									<span class="font-semibold text-gray-700">{m.dueDate()}:</span>
									<span class="ml-2">{formatDateOrDateTime(assessment.due_date)}</span>
								</div>
							{/if}
							{#if assessment.status}
								<div>
									<span class="font-semibold text-gray-700">{m.status()}:</span>
									<span class="ml-2">{safeTranslate(assessment.status)}</span>
								</div>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Workshop 2 -->
	<div id="workshop-2" class="my-12 scroll-mt-20 workshop-divider">
		<hr class="border-t-4 border-fuchsia-900" />
		<div class="text-center -mt-5 mb-12">
			<span class="bg-white px-6 py-2 text-xl font-bold text-fuchsia-900">
				{m.workshop()} 2 - {m.identifyRiskSources()}
			</span>
		</div>
	</div>

	<!-- RO/TO Couples Section -->
	{#if reportData.ro_to_couples.length > 0}
		<section class="mb-6 page-break-section">
			<h2
				class="text-lg font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2 flex items-center gap-2"
			>
				{m.roToCouples()}
				<span class="badge preset-tonal-secondary text-xs">{reportData.ro_to_couples.length}</span>
			</h2>
			<div class="space-y-4">
				{#each reportData.ro_to_couples as roto}
					<div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
						<h3 class="text-lg font-semibold text-gray-800 mb-2">
							{safeTranslate(roto.risk_origin)} - {roto.target_objective}
						</h3>
						<div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
							<div>
								<span class="font-semibold text-gray-700">{m.motivation()}:</span>
								<span class="ml-2">{safeTranslate(roto.motivation)}</span>
							</div>
							<div>
								<span class="font-semibold text-gray-700">{m.resources()}:</span>
								<span class="ml-2">{safeTranslate(roto.resources)}</span>
							</div>
							<div>
								<span class="font-semibold text-gray-700">{m.rotoActivity()}:</span>
								<span class="ml-2">{safeTranslate(roto.activity)}</span>
							</div>
							<div>
								<span class="font-semibold text-gray-700">{m.pertinence()}:</span>
								<span class="badge ml-2 {pertinenceColor[roto.pertinence]}"
									>{safeTranslate(roto.pertinence)}</span
								>
							</div>
						</div>
						{#if roto.feared_events.length > 0}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.fearedEvents()}:</span>
								<span class="ml-2 text-gray-600"
									>{reportData.feared_events
										.filter((fe) => roto.feared_events.some((id) => id.id === fe.id))
										.map((fe) => fe.name)
										.join(', ')}</span
								>
							</div>
						{/if}
						{#if roto.justification}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.justification()}:</span>
								<span class="ml-2 text-gray-600">{roto.justification}</span>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Workshop 3 -->
	<div id="workshop-3" class="my-12 scroll-mt-20 workshop-divider">
		<hr class="border-t-4 border-teal-500" />
		<div class="text-center -mt-5 mb-12">
			<span class="bg-white px-6 py-2 text-xl font-bold text-teal-500">
				{m.workshop()} 3 - {m.studyTheEcosystem()}
			</span>
		</div>
	</div>

	<!-- Stakeholders Section -->
	{#if reportData.stakeholders.length > 0}
		<section class="mb-6 page-break-section">
			<h2
				class="text-lg font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2 flex items-center gap-2"
			>
				{m.stakeholders()}
				<span class="badge preset-tonal-secondary text-xs">{reportData.stakeholders.length}</span>
			</h2>
			<div class="space-y-4">
				{#each reportData.stakeholders as stakeholder}
					<div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
						<h3 class="text-lg font-semibold text-gray-800 mb-3">
							{stakeholder.entity.str} ({safeTranslate(stakeholder.category)})
						</h3>
						<div class="flex flex-wrap gap-6 text-sm mb-2">
							<div class="flex flex-col">
								<span class="text-xs text-gray-500 mb-1">{m.currentCriticality()}</span>
								<span class="badge bg-blue-100 text-blue-800 font-bold text-base px-3 py-1"
									>{stakeholder.current_criticality}</span
								>
							</div>
							<div class="flex flex-col">
								<span class="text-xs text-gray-500 mb-1">{m.residualCriticality()}</span>
								<span class="badge bg-green-100 text-green-800 font-bold text-base px-3 py-1"
									>{stakeholder.residual_criticality}</span
								>
							</div>
						</div>
						{#if stakeholder.applied_controls.length > 0}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.appliedControls()}:</span>
								<span class="ml-2 text-gray-600"
									>{stakeholder.applied_controls.map((c) => c.str).join(', ')}</span
								>
							</div>
						{/if}
						{#if stakeholder.justification}
							<div class="mt-2 text-sm">
								<span class="font-semibold text-gray-700">{m.justification()}:</span>
								<span class="ml-2 text-gray-600">{stakeholder.justification}</span>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Ecosystem Radar Section - Current -->
	{#if reportData.stakeholders.length > 0 && reportData.radar}
		<section class="mb-6 radar-page">
			<h2
				class="text-lg font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2 text-center"
			>
				{m.ecosystemRadar()} - {m.current()}
			</h2>
			<div class="bg-white radar-chart-container" data-chart="radar-current">
				<EcosystemCircularRadarChart
					name="c_ecosystem_report"
					data={reportData.radar}
					type="current"
					classesContainer="w-full"
					height="h-[700px]"
				/>
			</div>
		</section>
	{/if}

	<!-- Ecosystem Radar Section - Residual -->
	{#if reportData.stakeholders.length > 0 && reportData.radar}
		<section class="mb-6 radar-page">
			<h2
				class="text-lg font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2 text-center"
			>
				{m.ecosystemRadar()} - {m.residual()}
			</h2>
			<div class="bg-white radar-chart-container" data-chart="radar-residual">
				<EcosystemCircularRadarChart
					name="r_ecosystem_report"
					data={reportData.radar}
					type="residual"
					classesContainer="w-full"
					height="h-[700px]"
				/>
			</div>
		</section>
	{/if}

	<!-- Scenarios Hierarchy Section -->
	{#if reportData.strategic_scenarios.length > 0}
		<section class="mb-6 strategic-scenarios-section">
			<h2 class="text-lg font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2">
				{m.strategicScenarios()} & {m.attackPaths()}
			</h2>
			<div class="space-y-6">
				{#each reportData.strategic_scenarios as scenario}
					{@const scenarioAttackPaths = reportData.attack_paths.filter(
						(ap) => ap.strategic_scenario.id === scenario.id
					)}
					<div class="border-2 border-purple-200 rounded-lg p-4">
						<!-- Strategic Scenario -->
						<div class="bg-purple-50 p-4 rounded-lg mb-4">
							<h3 class="text-lg font-semibold text-purple-900 mb-2">
								<i class="fa-solid fa-chess-knight mr-2"></i>{scenario.name}
							</h3>
							{#if scenario.description}
								<p class="text-gray-700 text-sm mb-3">{scenario.description}</p>
							{/if}
							<div class="flex flex-wrap gap-4 text-sm">
								<div>
									<span class="font-semibold text-gray-700">{m.gravity()}:</span>
									<span
										class="ml-2 px-2 py-1 rounded"
										style="background-color: {scenario.gravity.hexcolor}"
									>
										{safeTranslate(scenario.gravity.name)}
									</span>
								</div>
								{#if scenario.ref_id}
									<div>
										<span class="font-semibold text-gray-700">{m.refId()}:</span>
										<span class="ml-2">{scenario.ref_id}</span>
									</div>
								{/if}
							</div>
						</div>

						<!-- Attack Paths -->
						{#if scenarioAttackPaths.length > 0}
							<div class="ml-6 space-y-4">
								{#each scenarioAttackPaths as attackPath}
									{@const operationalScenario = reportData.operational_scenarios.find(
										(os) => os.attack_path.id === attackPath.id
									)}
									<div class="border border-teal-200 rounded-lg p-4 bg-teal-50">
										<!-- Attack Path -->
										<h4 class="text-md font-semibold text-teal-900 mb-2">
											<i class="fa-solid fa-route mr-2"></i>{attackPath.name}
										</h4>
										{#if attackPath.description}
											<p class="text-gray-700 text-sm mb-3">{attackPath.description}</p>
										{/if}
										<div class="flex flex-wrap gap-4 text-sm mb-2">
											<div>
												<span class="font-semibold text-gray-700">{m.riskOrigin()}:</span>
												<span class="ml-2">{safeTranslate(attackPath.risk_origin)}</span>
											</div>
											<div>
												<span class="font-semibold text-gray-700">{m.targetObjective()}:</span>
												<span class="ml-2">{attackPath.target_objective}</span>
											</div>
											{#if attackPath.ref_id}
												<div>
													<span class="font-semibold text-gray-700">{m.refId()}:</span>
													<span class="ml-2">{attackPath.ref_id}</span>
												</div>
											{/if}
										</div>
										{#if attackPath.stakeholders.length > 0}
											<div class="mt-2 text-sm">
												<span class="font-semibold text-gray-700">{m.stakeholders()}:</span>
												<span class="ml-2 text-gray-700">
													{attackPath.stakeholders
														.map((s) => {
															const stakeholderData = reportData.stakeholders.find(
																(st) => st.id === s.id
															);
															return stakeholderData
																? `${stakeholderData.entity.str} (${safeTranslate(stakeholderData.category)})`
																: s.str;
														})
														.join(', ')}
												</span>
											</div>
										{/if}

										<!-- Operational Scenario -->
										{#if operationalScenario}
											{@const opModes =
												reportData.operating_modes?.filter(
													(om) => om.operational_scenario.id === operationalScenario.id
												) || []}
											<div
												class="ml-6 mt-4 border-l-4 border-yellow-400 pl-4 bg-yellow-50 p-3 rounded"
											>
												<h5 class="text-sm font-semibold text-yellow-900 mb-2">
													<i class="fa-solid fa-gears mr-2"></i>{m.operationalScenario()}
												</h5>
												{#if operationalScenario.operating_modes_description && opModes.length === 0}
													<div class="text-sm mb-2">
														<span class="font-semibold text-gray-700"
															>{m.operatingModesDescription()}:</span
														>
														<p class="ml-2 text-gray-700 mt-1">
															{operationalScenario.operating_modes_description}
														</p>
													</div>
												{/if}
												<div class="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm mt-2">
													<div>
														<span class="font-semibold text-gray-700">{m.likelihood()}:</span>
														<span
															class="ml-2 px-2 py-1 rounded"
															style="background-color: {operationalScenario.likelihood.hexcolor}"
														>
															{safeTranslate(operationalScenario.likelihood.name)}
														</span>
													</div>
													<div>
														<span class="font-semibold text-gray-700">{m.gravity()}:</span>
														<span
															class="ml-2 px-2 py-1 rounded"
															style="background-color: {operationalScenario.gravity.hexcolor}"
														>
															{safeTranslate(operationalScenario.gravity.name)}
														</span>
													</div>
													<div>
														<span class="font-semibold text-gray-700">{m.riskLevel()}:</span>
														<span
															class="ml-2 px-2 py-1 rounded"
															style="background-color: {operationalScenario.risk_level.hexcolor ||
																'#f9fafb'}"
														>
															{safeTranslate(operationalScenario.risk_level.name)}
														</span>
													</div>
												</div>
												{#if operationalScenario.threats.length > 0}
													<div class="mt-2 text-sm">
														<span class="font-semibold text-gray-700">{m.threats()}:</span>
														<span class="ml-2 text-gray-700"
															>{operationalScenario.threats.map((t) => t.str).join(', ')}</span
														>
													</div>
												{/if}

												<!-- Operating Modes -->
												{#if opModes.length > 0}
													<div class="mt-3 space-y-2">
														<h6 class="text-sm font-semibold text-gray-800">
															<i class="fa-solid fa-list-check mr-1"></i>{m.operatingModes()}
															({opModes.length})
														</h6>
														{#each opModes as mode}
															<div class="bg-white border border-gray-200 rounded p-2 text-sm">
																<div class="font-medium text-gray-900">
																	{#if mode.ref_id}
																		<span class="text-gray-500">{mode.ref_id}:</span>
																	{/if}
																	{mode.name}
																</div>
																{#if mode.description}
																	<p class="text-gray-600 text-xs mt-1">{mode.description}</p>
																{/if}
																<div class="flex flex-wrap gap-3 mt-2">
																	<div>
																		<span class="font-semibold text-gray-700"
																			>{m.likelihood()}:</span
																		>
																		<span
																			class="ml-1 px-2 py-0.5 rounded text-xs"
																			style="background-color: {mode.likelihood.hexcolor}"
																		>
																			{safeTranslate(mode.likelihood.name)}
																		</span>
																	</div>
																	{#if mode.elementary_actions.length > 0}
																		<div>
																			<span class="font-semibold text-gray-700"
																				>{m.elementaryActions()}:</span
																			>
																			<span class="ml-1 text-gray-600"
																				>{mode.elementary_actions.length}</span
																			>
																		</div>
																	{/if}
																</div>
															</div>
														{/each}
													</div>
												{/if}
											</div>
										{/if}
									</div>
								{/each}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Workshop 4 -->
	<div id="workshop-4" class="my-12 scroll-mt-20 workshop-divider">
		<hr class="border-t-4 border-yellow-600" />
		<div class="text-center -mt-5 mb-12">
			<span class="bg-white px-6 py-2 text-xl font-bold text-yellow-600">
				{m.workshop()} 4 - {m.assessTheRiskScenarios()}
			</span>
		</div>
	</div>

	<!-- Operational Scenarios Section -->
	{#if reportData.operational_scenarios.length > 0}
		<section class="mb-6 page-break-section">
			<h2 class="text-lg font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2">
				{m.operationalScenarios()}
			</h2>
			{#if study.quotation_method}
				<div class="mb-4 text-sm">
					<span class="font-semibold text-gray-700">{m.quotationMethod()}:</span>
					<span class="ml-2">{safeTranslate(study.quotation_method)}</span>
				</div>
			{/if}
			<div class="space-y-6">
				{#each reportData.operational_scenarios as opScenario}
					{@const opModes =
						reportData.operating_modes?.filter(
							(om) => om.operational_scenario.id === opScenario.id
						) || []}
					<div class="border-2 border-yellow-200 rounded-lg p-4 bg-yellow-50">
						<div class="mb-4">
							<h3 class="text-lg font-semibold text-yellow-900 mb-2">
								<i class="fa-solid fa-gears mr-2"></i>{opScenario.ref_id || m.operationalScenario()}
							</h3>
							{#if opScenario.attack_path}
								<div class="text-sm mb-3">
									<span class="font-semibold text-gray-700">{m.attackPath()}:</span>
									<span class="ml-2 text-gray-700">{opScenario.attack_path.name}</span>
								</div>
							{/if}
							{#if opScenario.operating_modes_description && opModes.length === 0}
								<div class="text-sm mb-3">
									<span class="font-semibold text-gray-700">{m.operatingModesDescription()}:</span>
									<p class="ml-2 text-gray-700 mt-1">{opScenario.operating_modes_description}</p>
								</div>
							{/if}
							<div class="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
								<div>
									<span class="font-semibold text-gray-700">{m.likelihood()}:</span>
									<span
										class="ml-2 px-2 py-1 rounded text-xs font-medium"
										style="background-color: {opScenario.likelihood.hexcolor}"
									>
										{safeTranslate(opScenario.likelihood.name)}
									</span>
								</div>
								<div>
									<span class="font-semibold text-gray-700">{m.gravity()}:</span>
									<span
										class="ml-2 px-2 py-1 rounded text-xs font-medium"
										style="background-color: {opScenario.gravity.hexcolor}"
									>
										{safeTranslate(opScenario.gravity.name)}
									</span>
								</div>
								<div>
									<span class="font-semibold text-gray-700">{m.riskLevel()}:</span>
									<span
										class="ml-2 px-2 py-1 rounded text-xs font-medium"
										style="background-color: {opScenario.risk_level.hexcolor || '#gray'}"
									>
										{safeTranslate(opScenario.risk_level.name)}
									</span>
								</div>
							</div>
							{#if opScenario.threats && opScenario.threats.length > 0}
								<div class="mt-3 text-sm">
									<span class="font-semibold text-gray-700">{m.threats()}:</span>
									<span class="ml-2 text-gray-700">
										{opScenario.threats.map((t) => t.str).join(', ')}
									</span>
								</div>
							{/if}
							{#if opScenario.stakeholders && opScenario.stakeholders.length > 0}
								<div class="mt-2 text-sm">
									<span class="font-semibold text-gray-700">{m.stakeholders()}:</span>
									<span class="ml-2 text-gray-700">
										{opScenario.stakeholders
											.map((s) => {
												const stakeholderData = reportData.stakeholders.find(
													(st) => st.id === s.id
												);
												return stakeholderData
													? `${stakeholderData.entity.str} (${safeTranslate(stakeholderData.category)})`
													: s.str;
											})
											.join(', ')}
									</span>
								</div>
							{/if}
							{#if opScenario.justification}
								<div class="mt-2 text-sm">
									<span class="font-semibold text-gray-700">{m.justification()}:</span>
									<p class="ml-2 text-gray-600 mt-1">{opScenario.justification}</p>
								</div>
							{/if}
						</div>

						<!-- Operating Modes -->
						{#if opModes.length > 0}
							<div class="mt-4 pt-4 border-t border-yellow-300">
								<h4 class="text-md font-semibold text-gray-800 mb-3">
									<i class="fa-solid fa-cog mr-2"></i>{m.operatingModes()}
								</h4>
								<div class="space-y-3">
									{#each opModes as mode}
										<div class="bg-white border border-gray-200 rounded p-3">
											<div class="flex items-start gap-2 mb-2">
												{#if mode.is_selected}
													<span class="text-green-600 mt-0.5">
														<i class="fa-solid fa-check-circle"></i>
													</span>
												{:else}
													<span class="text-gray-400 mt-0.5">
														<i class="fa-regular fa-circle"></i>
													</span>
												{/if}
												<div class="flex-1">
													<div class="font-medium text-gray-900 text-sm">{mode.name}</div>
													{#if mode.description}
														<p class="text-gray-600 text-xs mt-1">{mode.description}</p>
													{/if}
												</div>
											</div>
											<div class="flex flex-wrap gap-3 ml-6">
												<div class="text-xs">
													<span class="font-semibold text-gray-700">{m.likelihood()}:</span>
													<span
														class="ml-1 px-2 py-0.5 rounded"
														style="background-color: {mode.likelihood.hexcolor}"
													>
														{safeTranslate(mode.likelihood.name)}
													</span>
												</div>
												{#if mode.elementary_actions.length > 0}
													<div class="text-xs">
														<span class="font-semibold text-gray-700">{m.elementaryActions()}:</span
														>
														<span class="ml-1 text-gray-600">{mode.elementary_actions.length}</span>
													</div>
												{/if}
											</div>
											<!-- Operating Mode Graph -->
											{#if mode.graph}
												<div class="mt-4 pt-4 border-t border-gray-200">
													<h5 class="text-xs font-semibold text-gray-700 mb-2">
														{m.killChain()}
													</h5>
													<div class="bg-gray-50 rounded p-2" data-chart="operating-mode-{mode.id}">
														<GraphComponent
															data={{ nodes: mode.graph.nodes, links: mode.graph.links }}
															panelNodes={mode.graph.panelNodes}
															linkFlow={false}
															height="400px"
															zoomLevel={0.6}
														/>
													</div>
												</div>
											{/if}
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<!-- Workshop 5 -->
	<div id="workshop-5" class="my-12 scroll-mt-20 workshop-divider">
		<hr class="border-t-4 border-red-500" />
		<div class="text-center -mt-5 mb-12">
			<span class="bg-white px-6 py-2 text-xl font-bold text-red-500">
				{m.workshop()} 5 - {m.validateTheTreatment()}
			</span>
		</div>
	</div>

	<!-- Risk Matrix Section -->
	{#if reportData.risk_matrix_data}
		{@const riskMatrix = reportData.risk_matrix_data.risk_matrix}
		{@const riskScenarios = reportData.risk_matrix_data.risk_scenarios}
		{@const inherentCluster = buildRiskCluster(riskScenarios, riskMatrix, 'inherent')}
		{@const currentCluster = buildRiskCluster(riskScenarios, riskMatrix, 'current')}
		{@const residualCluster = buildRiskCluster(riskScenarios, riskMatrix, 'residual')}
		<section class="mb-6 page-break-section">
			<h2 class="text-lg font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2">
				{m.riskMatrix()}
				{#if reportData.risk_matrix_data.risk_assessment}
					<span class="text-sm font-normal text-gray-600">
						- {reportData.risk_matrix_data.risk_assessment.name}
						{#if reportData.risk_matrix_data.risk_assessment.version}
							(v{reportData.risk_matrix_data.risk_assessment.version})
						{/if}
					</span>
				{/if}
			</h2>

			<!-- Risk Scenarios Summary -->
			{#if riskScenarios.length > 0}
				<div class="mb-6 overflow-x-auto">
					<table class="min-w-full divide-y divide-gray-200 border border-gray-300">
						<thead class="bg-gray-50">
							<tr>
								<th
									class="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider border-r"
									>{m.refId()}</th
								>
								<th
									class="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider border-r"
									>{m.name()}</th
								>
								{#if inherentRiskEnabled}
									<th
										class="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider border-r"
										>{m.inherentRisk()}</th
									>
								{/if}
								<th
									class="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider border-r"
									>{m.currentRisk()}</th
								>
								<th
									class="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider"
									>{m.residualRisk()}</th
								>
							</tr>
						</thead>
						<tbody class="bg-white divide-y divide-gray-200">
							{#each riskScenarios as scenario}
								<tr class="hover:bg-gray-50">
									<td class="px-4 py-3 text-sm font-medium text-gray-900 border-r"
										>{scenario.ref_id || '--'}</td
									>
									<td class="px-4 py-3 text-sm text-gray-700 border-r">{scenario.name}</td>
									{#if inherentRiskEnabled}
										<td class="px-4 py-3 text-sm border-r">
											{#if scenario.inherent_level}
												<span
													class="px-2 py-1 rounded text-xs font-medium"
													style="background-color: {scenario.inherent_level.hexcolor}"
												>
													{safeTranslate(scenario.inherent_level.name)}
												</span>
											{:else}
												<span class="text-gray-400">--</span>
											{/if}
										</td>
									{/if}
									<td class="px-4 py-3 text-sm border-r">
										{#if scenario.current_level}
											<span
												class="px-2 py-1 rounded text-xs font-medium"
												style="background-color: {scenario.current_level.hexcolor}"
											>
												{safeTranslate(scenario.current_level.name)}
											</span>
										{:else}
											<span class="text-gray-400">--</span>
										{/if}
									</td>
									<td class="px-4 py-3 text-sm">
										{#if scenario.residual_level}
											<span
												class="px-2 py-1 rounded text-xs font-medium"
												style="background-color: {scenario.residual_level.hexcolor}"
											>
												{safeTranslate(scenario.residual_level.name)}
											</span>
										{:else}
											<span class="text-gray-400">--</span>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
			<div class="space-y-8">
				{#if inherentRiskEnabled}
					<div data-chart="risk-matrix-inherent">
						<h3 class="font-bold p-2 m-2 text-lg text-center">{m.inherentRisk()}</h3>
						<RiskMatrix
							{riskMatrix}
							matrixName="inherent"
							data={inherentCluster}
							dataItemComponent={RiskScenarioItem}
							{useBubbles}
						/>
					</div>
				{/if}
				<div data-chart="risk-matrix-current">
					<h3 class="font-bold p-2 m-2 text-lg text-center">{m.currentRisk()}</h3>
					<RiskMatrix
						{riskMatrix}
						matrixName="current"
						data={currentCluster}
						dataItemComponent={RiskScenarioItem}
						{useBubbles}
					/>
				</div>
				<div data-chart="risk-matrix-residual">
					<h3 class="font-bold p-2 m-2 text-lg text-center">{m.residualRisk()}</h3>
					<RiskMatrix
						{riskMatrix}
						matrixName="residual"
						data={residualCluster}
						dataItemComponent={RiskScenarioItem}
						showLegend={true}
						{useBubbles}
					/>
				</div>
			</div>
		</section>
	{/if}

	<!-- Treatment Plan Section -->
	{#if reportData.compliance_action_plans?.length > 0 || reportData.risk_action_plan}
		<section class="mb-6 page-break-section">
			<h2 class="text-lg font-semibold text-gray-900 mb-4 border-b border-gray-200 pb-2">
				{m.treatmentPlan()}
			</h2>

			<!-- Compliance Assessment Action Plans -->
			{#if reportData.compliance_action_plans && reportData.compliance_action_plans.length > 0}
				<div class="space-y-6">
					{#each reportData.compliance_action_plans as actionPlan}
						{#if actionPlan.applied_controls.length > 0}
							<div class="border border-blue-200 rounded-lg p-4 bg-blue-50">
								<h3 class="text-lg font-semibold text-blue-900 mb-3">
									<i class="fa-solid fa-clipboard-check mr-2"></i>
									{actionPlan.assessment_name}
									{#if actionPlan.framework}
										<span class="text-sm font-normal text-blue-700">
											({actionPlan.framework})
										</span>
									{/if}
								</h3>
								<div class="overflow-x-auto">
									<table class="min-w-full divide-y divide-gray-200 bg-white rounded border">
										<thead class="bg-gray-50">
											<tr>
												<th class="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase"
													>{m.name()}</th
												>
												<th class="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase"
													>{m.priority()}</th
												>
												<th class="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase"
													>{m.status()}</th
												>
												<th class="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase"
													>{m.owner()}</th
												>
												<th class="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase"
													>{m.eta()}</th
												>
											</tr>
										</thead>
										<tbody class="divide-y divide-gray-200">
											{#each actionPlan.applied_controls as control}
												<tr class="hover:bg-gray-50">
													<td class="px-3 py-2 text-sm text-gray-900">{control.name}</td>
													<td class="px-3 py-2 text-sm">
														{#if control.priority}
															<span class="px-2 py-1 rounded text-xs font-medium"
																>{safeTranslate(control.priority)}</span
															>
														{:else}
															--
														{/if}
													</td>
													<td class="px-3 py-2 text-sm">
														{#if control.status}
															<span class="px-2 py-1 rounded text-xs font-medium"
																>{safeTranslate(control.status)}</span
															>
														{:else}
															--
														{/if}
													</td>
													<td class="px-3 py-2 text-sm">
														{#if control.owner}
															{control.owner.str}
														{:else}
															--
														{/if}
													</td>
													<td class="px-3 py-2 text-sm">
														{control.eta ? formatDateOrDateTime(control.eta) : '--'}
													</td>
												</tr>
											{/each}
										</tbody>
									</table>
								</div>
							</div>
						{/if}
					{/each}
				</div>
			{/if}

			<!-- Risk Assessment Action Plan -->
			{#if reportData.risk_action_plan && reportData.risk_action_plan.applied_controls.length > 0}
				<div class="border border-red-200 rounded-lg p-4 bg-red-50 mt-6">
					<h3 class="text-lg font-semibold text-red-900 mb-3">
						<i class="fa-solid fa-shield-halved mr-2"></i>
						{reportData.risk_action_plan.risk_assessment_name}
						<span class="text-sm font-normal text-red-700">({m.riskAssessment()})</span>
					</h3>
					<div class="overflow-x-auto">
						<table class="min-w-full divide-y divide-gray-200 bg-white rounded border">
							<thead class="bg-gray-50">
								<tr>
									<th class="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase"
										>{m.name()}</th
									>
									<th class="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase"
										>{m.priority()}</th
									>
									<th class="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase"
										>{m.status()}</th
									>
									<th class="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase"
										>{m.owner()}</th
									>
									<th class="px-3 py-2 text-left text-xs font-medium text-gray-700 uppercase"
										>{m.eta()}</th
									>
								</tr>
							</thead>
							<tbody class="divide-y divide-gray-200">
								{#each reportData.risk_action_plan.applied_controls as control}
									<tr class="hover:bg-gray-50">
										<td class="px-3 py-2 text-sm text-gray-900">{control.name}</td>
										<td class="px-3 py-2 text-sm">
											{#if control.priority}
												<span class="px-2 py-1 rounded text-xs font-medium"
													>{safeTranslate(control.priority)}</span
												>
											{:else}
												--
											{/if}
										</td>
										<td class="px-3 py-2 text-sm">
											{#if control.status}
												<span class="px-2 py-1 rounded text-xs font-medium"
													>{safeTranslate(control.status)}</span
												>
											{:else}
												--
											{/if}
										</td>
										<td class="px-3 py-2 text-sm">
											{#if control.owner}
												{control.owner.str}
											{:else}
												--
											{/if}
										</td>
										<td class="px-3 py-2 text-sm">
											{control.eta ? formatDateOrDateTime(control.eta) : '--'}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			{/if}
		</section>
	{/if}
</div>

<style>
	:global(html) {
		scroll-behavior: smooth;
	}

	/* Print styles for PDF export */
	@media print {
		/* Hide elements that shouldn't be printed */
		:global(.no-print),
		:global(.app-shell > .sidebar),
		:global(.app-bar),
		:global(nav),
		:global(header),
		:global(.breadcrumbs),
		:global([class*='AppBar']),
		:global(.drawer),
		:global([class*='drawer']),
		:global(.sidebar),
		:global([class*='sidebar']),
		:global(aside),
		:global([role='complementary']),
		:global(button[aria-label*='menu']),
		:global(button[aria-label*='Menu']),
		:global(button[class*='chevron']),
		:global([class*='Chevron']),
		:global(button[class*='btn-icon']),
		:global(.btn-icon),
		:global([class*='drawer-toggle']),
		:global([class*='menu-toggle']),
		:global(button.fixed),
		:global(.fixed button) {
			display: none !important;
			visibility: hidden !important;
			height: 0 !important;
			width: 0 !important;
			overflow: hidden !important;
			position: absolute !important;
			left: -9999px !important;
		}

		/* Hide navigation elements only (not all buttons/links) */
		.no-print button,
		.no-print a,
		.no-print i.fa-arrow-left {
			display: none !important;
		}

		/* Allow workshop HR lines to show */
		.workshop-divider hr {
			display: block !important;
			visibility: visible !important;
			height: auto !important;
			width: 100% !important;
			position: static !important;
			left: auto !important;
		}

		/* Ensure study header starts at top of first page */
		.bg-white.shadow-sm:first-of-type {
			padding-top: 0 !important;
			margin-top: 0 !important;
		}

		/* Default page setup - portrait */
		@page {
			size: A3 portrait;
			margin: 1.5cm 2cm;
		}

		/* Landscape page for wide charts */
		@page landscape {
			size: A3 landscape;
			margin: 1.5cm 2cm;
		}

		/* Apply landscape orientation to specific sections */
		.landscape-page {
			page: landscape;
			page-break-before: always;
			page-break-after: always;
		}

		/* Reset all layout constraints */
		:global(html),
		:global(body) {
			margin: 0 !important;
			padding: 0 !important;
			width: 100% !important;
			height: auto !important;
			overflow: visible !important;
			background: white !important;
		}

		/* Reset main content area */
		:global(main) {
			margin: 0 !important;
			padding: 0 !important;
			background: white !important;
			min-height: auto !important;
			width: 100% !important;
			max-width: 100% !important;
		}

		/* Hide app shell wrapper completely */
		:global(.app-shell) {
			background: white !important;
		}

		/* Remove any background gradients */
		:global([class*='bg-linear']),
		:global([class*='from-']),
		:global([class*='to-']) {
			background: white !important;
		}

		/* Reset report container */
		:global(.max-w-7xl) {
			max-width: 100% !important;
			margin: 0 !important;
			padding: 0 !important;
			box-sizing: border-box !important;
		}

		/* Remove shadow and positioning from report container */
		:global(.relative) {
			position: static !important;
		}

		/* Ensure content fills the page properly */
		:global(.bg-white) {
			background: white !important;
		}

		/* Remove shadows for cleaner print */
		:global(.shadow-sm),
		:global(.shadow-md),
		:global(.shadow-lg) {
			box-shadow: none !important;
		}

		/* Page breaks before major sections - DISABLED in favor of workshop breaks */
		.page-break-section {
			page-break-before: auto !important;
			break-before: auto !important;
		}

		/* Prevent page breaks inside important elements */
		.card,
		.border {
			page-break-inside: avoid !important;
			break-inside: avoid !important;
		}

		/* Allow tables to break if needed but avoid orphans */
		table {
			page-break-inside: auto !important;
		}

		tr {
			page-break-inside: avoid !important;
			page-break-after: auto !important;
		}

		thead {
			display: table-header-group !important;
		}

		/* Force page breaks before workshop dividers */
		.workshop-divider {
			page-break-before: always !important;
			break-before: page !important;
			margin: 2cm 0 1cm 0 !important;
			padding-top: 0 !important;
		}

		/* First workshop shouldn't break */
		#workshop-1 {
			page-break-before: auto !important;
			break-before: auto !important;
			margin-top: 2cm !important;
		}

		/* Workshop title styling */
		.workshop-divider hr {
			margin-bottom: 0 !important;
			border-width: 3px !important;
		}

		.workshop-divider .text-center {
			margin-top: -0.8em !important;
			margin-bottom: 1.5cm !important;
		}

		.workshop-divider .text-center span {
			padding: 0.3em 1.5em !important;
			background: white !important;
			display: inline-block !important;
			line-height: 1 !important;
		}

		/* Ensure workshop headers stay with content */
		h1,
		h2,
		h3 {
			page-break-after: avoid !important;
			break-after: avoid !important;
			page-break-inside: avoid !important;
		}

		/* Ensure charts render at good quality and fit on page */
		[data-chart] {
			width: 100% !important;
			max-width: 100% !important;
			page-break-inside: avoid !important;
			break-inside: avoid !important;
			margin: 0.5cm 0 !important;
			overflow: hidden !important;
		}

		/* Scale down large charts to fit */
		[data-chart] > * {
			max-width: 100% !important;
			max-height: 20cm !important;
			height: auto !important;
			width: auto !important;
			transform: scale(0.95) !important;
			transform-origin: top left !important;
		}

		/* Specific fixes for radar charts */
		[data-chart='radar-current'],
		[data-chart='radar-residual'] {
			max-height: 25cm !important;
			margin-left: -1cm !important;
		}

		[data-chart='radar-current'] > *,
		[data-chart='radar-residual'] > * {
			max-height: 25cm !important;
		}

		/* Radar pages - one chart per page, centered */
		.radar-page {
			page-break-before: always !important;
			page-break-after: always !important;
		}

		.radar-page h2 {
			text-align: center !important;
		}

		/* Strategic scenarios section gets page break */
		.strategic-scenarios-section {
			page-break-before: always !important;
		}

		/* Fix operating mode graphs - scale to fit and wrap if needed */
		[data-chart^='operating-mode-'] {
			max-width: 100% !important;
			max-height: 18cm !important;
			overflow: hidden !important;
			page-break-inside: avoid !important;
			margin: 1cm 0 !important;
		}

		[data-chart^='operating-mode-'] > * {
			max-width: 100% !important;
			max-height: 18cm !important;
			transform: scale(0.85) !important;
			transform-origin: top left !important;
		}

		/* Ensure operating mode SVG elements scale properly */
		[data-chart^='operating-mode-'] svg {
			max-width: 100% !important;
			height: auto !important;
		}

		/* Ensure chart containers don't create extra space */
		:global([class*='h-[']) {
			height: auto !important;
			max-height: 25cm !important;
		}

		/* Make tables print nicely */
		table {
			border-collapse: collapse !important;
			width: 100% !important;
			font-size: 8pt !important;
		}

		table,
		th,
		td {
			border: 1px solid #999 !important;
		}

		th {
			background-color: #f3f4f6 !important;
			font-weight: bold !important;
			padding: 4px 6px !important;
		}

		td {
			padding: 3px 6px !important;
		}

		/* Ensure badges and colored elements print well */
		.badge,
		[class*='bg-'],
		[style*='background-color'] {
			-webkit-print-color-adjust: exact !important;
			print-color-adjust: exact !important;
			color-adjust: exact !important;
		}

		/* Better spacing for sections */
		section {
			margin-bottom: 1rem !important;
		}

		/* Remove fixed positioning */
		:global(.fixed) {
			position: static !important;
		}

		/* Ensure proper link rendering */
		a {
			color: inherit !important;
			text-decoration: none !important;
		}

		/* Make sure icons print */
		:global(.fa-solid),
		:global(.fa-regular) {
			-webkit-print-color-adjust: exact !important;
			print-color-adjust: exact !important;
		}

		/* Optimize grid layouts for print */
		.grid {
			grid-template-columns: repeat(2, 1fr) !important;
		}

		/* Optimize font sizes for A3 */
		body {
			font-size: 10pt !important;
		}

		h1 {
			font-size: 18pt !important;
		}

		h2 {
			font-size: 14pt !important;
		}

		h3 {
			font-size: 12pt !important;
		}

		/* Better table sizing for A3 */
		table {
			font-size: 9pt !important;
		}

		/* Ensure workshop dividers print nicely */
		hr {
			page-break-after: avoid !important;
		}
	}
</style>
