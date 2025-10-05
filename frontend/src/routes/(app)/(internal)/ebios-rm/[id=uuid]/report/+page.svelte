<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import RiskMatrix from '$lib/components/RiskMatrix/RiskMatrix.svelte';
	import RiskScenarioItem from '$lib/components/RiskMatrix/RiskScenarioItem.svelte';
	import type { PageData } from './$types';
	import type { RiskMatrixJsonDefinition, RiskScenario } from '$lib/utils/types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	pageTitle.set('EBIOS RM Study Report');

	const { reportData } = data;
	const study = reportData.study;

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

<div class="bg-white shadow-sm p-8 max-w-7xl mx-auto">
	<!-- Back to Study Link -->
	<div class="mb-4">
		<Anchor
			breadcrumbAction="push"
			href={`/ebios-rm/${study.id}`}
			class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
		>
			<i class="fa-solid fa-arrow-left"></i>
			<p>{m.backToStudy()}</p>
		</Anchor>
	</div>

	<!-- Study Header -->
	<div class="mb-8">
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
		<section class="mb-8">
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
		<section class="mb-8">
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
		<section class="mb-8">
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
		<section class="mb-8">
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

	<!-- Scenarios Hierarchy Section -->
	{#if reportData.strategic_scenarios.length > 0}
		<section class="mb-8">
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
												{#if operationalScenario.operating_modes_description}
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

	<!-- Risk Matrix Section -->
	{#if reportData.risk_matrix_data}
		{@const riskMatrix = reportData.risk_matrix_data.risk_matrix}
		{@const riskScenarios = reportData.risk_matrix_data.risk_scenarios}
		{@const currentCluster = buildRiskCluster(riskScenarios, riskMatrix, 'current')}
		{@const residualCluster = buildRiskCluster(riskScenarios, riskMatrix, 'residual')}
		<section class="mb-8">
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
				<div>
					<h3 class="font-bold p-2 m-2 text-lg text-center">{m.currentRisk()}</h3>
					<RiskMatrix
						{riskMatrix}
						matrixName="current"
						data={currentCluster}
						dataItemComponent={RiskScenarioItem}
						useBubbles={true}
					/>
				</div>
				<div>
					<h3 class="font-bold p-2 m-2 text-lg text-center">{m.residualRisk()}</h3>
					<RiskMatrix
						{riskMatrix}
						matrixName="residual"
						data={residualCluster}
						dataItemComponent={RiskScenarioItem}
						showLegend={true}
						useBubbles={true}
					/>
				</div>
			</div>
		</section>
	{/if}
</div>
