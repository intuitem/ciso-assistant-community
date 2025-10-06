<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import RiskMatrix from '$lib/components/RiskMatrix/RiskMatrix.svelte';
	import RiskScenarioItem from '$lib/components/RiskMatrix/RiskScenarioItem.svelte';
	import EcosystemRadarChart from '$lib/components/Chart/EcosystemRadarChart.svelte';
	import GraphComponent from '../../../operating-modes/[id=uuid]/graph/OperatingModeGraph.svelte';
	import type { PageData } from './$types';
	import type { RiskMatrixJsonDefinition, RiskScenario } from '$lib/utils/types';
	import { toPng, toSvg } from 'html-to-image';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	pageTitle.set('EBIOS RM Study Report');

	const { reportData } = data;
	const study = reportData.study;
	const useBubbles = data.useBubbles;
	const inherentRiskEnabled = data.inherentRiskEnabled;

	let isGeneratingPDF = $state(false);

	async function exportPDF() {
		isGeneratingPDF = true;
		try {
			const charts: Record<string, string> = {};

			// Capture radar charts
			const radarCurrent = document.querySelector('[data-chart="radar-current"]');
			if (radarCurrent) {
				charts.radarCurrent = await toPng(radarCurrent as HTMLElement);
			}

			const radarResidual = document.querySelector('[data-chart="radar-residual"]');
			if (radarResidual) {
				charts.radarResidual = await toPng(radarResidual as HTMLElement);
			}

			// Capture risk matrices
			const riskMatrixInherent = document.querySelector('[data-chart="risk-matrix-inherent"]');
			if (riskMatrixInherent) {
				charts.riskMatrixInherent = await toPng(riskMatrixInherent as HTMLElement);
			}

			const riskMatrixCurrent = document.querySelector('[data-chart="risk-matrix-current"]');
			if (riskMatrixCurrent) {
				charts.riskMatrixCurrent = await toPng(riskMatrixCurrent as HTMLElement);
			}

			const riskMatrixResidual = document.querySelector('[data-chart="risk-matrix-residual"]');
			if (riskMatrixResidual) {
				charts.riskMatrixResidual = await toPng(riskMatrixResidual as HTMLElement);
			}

			// Capture operating mode graphs as SVG with Font Awesome CSS embedded
			const graphElements = document.querySelectorAll('[data-chart^="operating-mode-"]');
			const operatingModeGraphs: Record<string, string> = {};

			// Fetch Font Awesome CSS from CDN
			let fontAwesomeCSS = '';
			try {
				fontAwesomeCSS = await fetch(
					'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.1/css/all.min.css'
				)
					.then((r) => r.text())
					.catch(() => '');
			} catch (e) {
				console.warn('Could not fetch Font Awesome CSS:', e);
			}

			for (const graph of Array.from(graphElements)) {
				const modeId = graph.getAttribute('data-chart')?.replace('operating-mode-', '');
				if (modeId) {
					// Force inline styles to ensure backgrounds are white
					const element = graph as HTMLElement;
					const originalStyle = element.style.cssText;
					element.style.backgroundColor = 'white';

					// Find all SVG elements and ensure fills are preserved
					const svgElements = element.querySelectorAll('rect, path, circle');
					const originalFills = new Map();
					svgElements.forEach((el) => {
						const svgEl = el as SVGElement;
						originalFills.set(svgEl, svgEl.style.fill);
						const computedFill = window.getComputedStyle(svgEl).fill;
						if (computedFill && computedFill !== 'none') {
							svgEl.style.fill = computedFill;
						}
					});

					// Use toSvg with Font Awesome CSS embedded
					operatingModeGraphs[modeId] = await toSvg(element, {
						cacheBust: true,
						fontEmbedCSS: fontAwesomeCSS,
						backgroundColor: '#ffffff'
					});

					// Restore original styles
					element.style.cssText = originalStyle;
					svgElements.forEach((el) => {
						const svgEl = el as SVGElement;
						const originalFill = originalFills.get(svgEl);
						if (originalFill !== undefined) {
							svgEl.style.fill = originalFill;
						}
					});
				}
			}
			charts.operatingModeGraphs = JSON.stringify(operatingModeGraphs);

			// Use form action to send to server
			const formData = new FormData();
			formData.append('charts', JSON.stringify({ charts }));

			const response = await fetch('?/exportPdf', {
				method: 'POST',
				body: formData
			});

			if (!response.ok) {
				throw new Error('Failed to generate PDF');
			}

			const result = await response.json();

			if (result.type === 'success') {
				// Parse the devalue serialized data
				const actionResult =
					typeof result.data === 'string' ? JSON.parse(result.data) : result.data;

				// Handle devalue serialization format
				// Index 0: metadata object {success: 1, pdf: 2}
				// Index 1: boolean (true)
				// Index 2: array containing the actual PDF bytes
				const actualData = Array.isArray(actionResult) ? actionResult[0] : actionResult;

				if (actualData.success && actualData.pdf !== undefined) {
					// The PDF bytes are in an array at index actualData.pdf (which is 2)
					const pdfIndices = actionResult[actualData.pdf];

					if (!Array.isArray(pdfIndices)) {
						throw new Error('Invalid PDF data structure');
					}

					// Dereference the indices to get actual byte values
					const pdfBytes = pdfIndices.map((index) => actionResult[index]);

					// Check if PDF starts with correct magic bytes (37 80 68 70 = %PDF)
					if (
						pdfBytes[0] !== 37 ||
						pdfBytes[1] !== 80 ||
						pdfBytes[2] !== 68 ||
						pdfBytes[3] !== 70
					) {
						throw new Error('Invalid PDF data received');
					}

					// Convert array back to Blob
					const pdfArray = new Uint8Array(pdfBytes);
					const blob = new Blob([pdfArray], { type: 'application/pdf' });

					const url = window.URL.createObjectURL(blob);
					const a = document.createElement('a');
					a.href = url;
					a.download = `ebios-rm-report-${study.name}.pdf`;
					document.body.appendChild(a);
					a.click();
					document.body.removeChild(a);
					window.URL.revokeObjectURL(url);
				} else {
					throw new Error('Invalid response from server');
				}
			} else {
				throw new Error('Invalid response from server');
			}
		} catch (error) {
			console.error('Error generating PDF:', error);
			alert('Failed to generate PDF. Please try again.');
		} finally {
			isGeneratingPDF = false;
		}
	}

	// Build risk cluster for current risk level
	const buildRiskCluster = (
		scenarios: RiskScenario[],
		risk_matrix: any,
		risk: 'current' | 'residual' | 'inherent'
	) => {
		const parsedRiskMatrix: RiskMatrixJsonDefinition = JSON.parse(risk_matrix.json_definition);
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

<div class="bg-white shadow-sm p-4 max-w-7xl mx-auto">
	<!-- Back to Study Link and Export Button -->
	<div class="mb-4 flex justify-between items-center">
		<Anchor
			breadcrumbAction="push"
			href={`/ebios-rm/${study.id}`}
			class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
		>
			<i class="fa-solid fa-arrow-left"></i>
			<p>{m.backToStudy()}</p>
		</Anchor>
		<!-- <button -->
		<!-- 	onclick={exportPDF} -->
		<!-- 	disabled={isGeneratingPDF} -->
		<!-- 	class="btn preset-filled-primary-500 flex items-center gap-2" -->
		<!-- > -->
		<!-- 	{#if isGeneratingPDF} -->
		<!-- 		<i class="fa-solid fa-spinner fa-spin"></i> -->
		<!-- 		<span>{m.generating()}...</span> -->
		<!-- 	{:else} -->
		<!-- 		<i class="fa-solid fa-file-pdf"></i> -->
		<!-- 		<span>{m.exportPdf()}</span> -->
		<!-- 	{/if} -->
		<!-- </button> -->
	</div>

	<!-- Study Header -->
	<div class="mb-6">
		<h1 class="text-3xl font-bold text-gray-900 mb-2">{study.name}</h1>
		{#if study.description}
			<p class="text-gray-600 mb-4">{study.description}</p>
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
			<div>
				<span class="font-semibold text-gray-700">{m.eta()}:</span>
				<span class="ml-2">{study.eta ? formatDateOrDateTime(study.eta) : 'N/A'}</span>
			</div>
			<div>
				<span class="font-semibold text-gray-700">{m.dueDate()}:</span>
				<span class="ml-2">{study.due_date ? formatDateOrDateTime(study.due_date) : 'N/A'}</span>
			</div>
		</div>
	</div>

	<!-- Feared Events Section -->
	{#if reportData.feared_events.length > 0}
		<section class="mb-6">
			<h2 class="text-2xl font-bold text-gray-900 mb-4 border-b-2 border-gray-200 pb-2">
				{m.fearedEvents()} ({reportData.feared_events.length})
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
		<section class="mb-6">
			<h2 class="text-2xl font-bold text-gray-900 mb-4 border-b-2 border-gray-200 pb-2">
				{m.complianceAssessments()} ({reportData.compliance_assessments.length})
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

	<!-- RO/TO Couples Section -->
	{#if reportData.ro_to_couples.length > 0}
		<section class="mb-6">
			<h2 class="text-2xl font-bold text-gray-900 mb-4 border-b-2 border-gray-200 pb-2">
				{m.roToCouples()} ({reportData.ro_to_couples.length})
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
								<span class="font-semibold text-gray-700">{m.activity()}:</span>
								<span class="ml-2">{safeTranslate(roto.activity)}</span>
							</div>
							<div>
								<span class="font-semibold text-gray-700">{m.pertinence()}:</span>
								<span class="ml-2">{safeTranslate(roto.pertinence)}</span>
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

	<!-- Stakeholders Section -->
	{#if reportData.stakeholders.length > 0}
		<section class="mb-6">
			<h2 class="text-2xl font-bold text-gray-900 mb-4 border-b-2 border-gray-200 pb-2">
				{m.stakeholders()} ({reportData.stakeholders.length})
			</h2>
			<div class="space-y-4">
				{#each reportData.stakeholders as stakeholder}
					<div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
						<h3 class="text-lg font-semibold text-gray-800 mb-2">
							{stakeholder.entity.str} ({safeTranslate(stakeholder.category_raw)})
						</h3>
						<div class="grid grid-cols-2 gap-4 text-sm">
							<div>
								<span class="font-semibold text-gray-700">{m.currentCriticality()}:</span>
								<span class="ml-2">{stakeholder.current_criticality}</span>
							</div>
							<div>
								<span class="font-semibold text-gray-700">{m.residualCriticality()}:</span>
								<span class="ml-2">{stakeholder.residual_criticality}</span>
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

	<!-- Ecosystem Radar Section -->
	{#if reportData.stakeholders.length > 0 && reportData.radar}
		<section class="mb-6">
			<h2 class="text-2xl font-bold text-gray-900 mb-4 border-b-2 border-gray-200 pb-2">
				{m.ecosystemRadar()}
			</h2>
			<div class="bg-white flex gap-4">
				<div class="w-1/2" data-chart="radar-current">
					<EcosystemRadarChart
						title={m.current()}
						name="c_ecosystem_report"
						data={reportData.radar.current}
						classesContainer="w-full"
						height="h-[800px]"
					/>
				</div>
				<div class="w-1/2" data-chart="radar-residual">
					<EcosystemRadarChart
						title={m.residual()}
						name="r_ecosystem_report"
						data={reportData.radar.residual}
						classesContainer="w-full"
						height="h-[800px]"
					/>
				</div>
			</div>
		</section>
	{/if}

	<!-- Scenarios Hierarchy Section -->
	{#if reportData.strategic_scenarios.length > 0}
		<section class="mb-6">
			<h2 class="text-2xl font-bold text-gray-900 mb-4 border-b-2 border-gray-200 pb-2">
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
																? `${stakeholderData.entity.str} (${safeTranslate(stakeholderData.category_raw)})`
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

	<!-- Operational Scenarios Section -->
	{#if reportData.operational_scenarios.length > 0}
		<section class="mb-6">
			<h2 class="text-2xl font-bold text-gray-900 mb-4 border-b-2 border-gray-200 pb-2">
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
													? `${stakeholderData.entity.str} (${safeTranslate(stakeholderData.category_raw)})`
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

	<!-- Risk Matrix Section -->
	{#if reportData.risk_matrix_data}
		{@const riskMatrix = reportData.risk_matrix_data.risk_matrix}
		{@const riskScenarios = reportData.risk_matrix_data.risk_scenarios}
		{@const inherentCluster = buildRiskCluster(riskScenarios, riskMatrix, 'inherent')}
		{@const currentCluster = buildRiskCluster(riskScenarios, riskMatrix, 'current')}
		{@const residualCluster = buildRiskCluster(riskScenarios, riskMatrix, 'residual')}
		<section class="mb-6">
			<h2 class="text-2xl font-bold text-gray-900 mb-4 border-b-2 border-gray-200 pb-2">
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
		<section class="mb-6">
			<h2 class="text-2xl font-bold text-gray-900 mb-4 border-b-2 border-gray-200 pb-2">
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
