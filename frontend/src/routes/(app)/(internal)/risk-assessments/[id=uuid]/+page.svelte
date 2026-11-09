<script lang="ts">
	import ExportModal, { type ExportGroup } from '#lib/components/Modals/ExportModal.svelte';
	import { page } from '$app/state';
	import CreateModal from '#lib/components/Modals/CreateModal.svelte';
	import ModelTable from '#lib/components/ModelTable/ModelTable.svelte';
	import RiskMatrix from '#lib/components/RiskMatrix/RiskMatrix.svelte';
	import { URL_MODEL_MAP, getModelInfo } from '#lib/utils/crud.js';
	import ScenarioSelectionBar from '#lib/components/ScenarioSelection/ScenarioSelectionBar.svelte';
	import { selectionSummary } from '#lib/components/ScenarioSelection/labels.js';
	import {
		DEFAULT_LINK_TYPE,
		LINK_TYPE_PARAM,
		hasSelection,
		readSelection,
		selectionParams,
		unprefixedSelection,
		withParams
	} from '#lib/utils/scenarioSelection.js';
	import type { RiskMatrixJsonDefinition, RiskScenario } from '#lib/utils/types.js';
	import Anchor from '#lib/components/Anchor/Anchor.svelte';
	import AuditTrailButton from '#lib/components/AuditTrail/AuditTrailButton.svelte';
	import RiskScenarioItem from '#lib/components/RiskMatrix/RiskScenarioItem.svelte';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { m } from '#paraglide/messages.js';
	import { canPerformActionOnObject } from '#lib/utils/access-control.js';
	import { formatDate } from '#lib/utils/datetime.js';
	import { getLocale } from '#paraglide/runtime.js';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '#lib/components/Modals/stores.js';
	import { Progress } from '@skeletonlabs/skeleton-svelte';
	import MarkdownRenderer from '#lib/components/MarkdownRenderer.svelte';
	import List from '#lib/components/List/List.svelte';
	import ConfirmModal from '#lib/components/Modals/ConfirmModal.svelte';
	import SyncToActionsRiskModal from '#lib/components/Modals/SyncToActionsRiskModal.svelte';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import ValidationFlowsSection from '#lib/components/ValidationFlows/ValidationFlowsSection.svelte';
	import { refreshAll } from '$app/navigation';

	let { data, form } = $props();

	const showRisks = true;
	const useBubbles = data.useBubbles;
	const risk_assessment = $derived(data.risk_assessment);

	// The selection bar filters the table, the matrices, the action plan link and
	// the exports alike; the table keeps no filters of its own.
	const selection = $derived(data.selection);
	const scoped = $derived(hasSelection(page.url.searchParams));
	const selectionQuery = $derived(selectionParams(page.url.searchParams));
	const selectedScenarios = $derived.by(() => {
		if (!scoped || !selection) return risk_assessment.risk_scenarios;
		const ids = new Set(selection.ids);
		return risk_assessment.risk_scenarios.filter((s: { id: string }) => ids.has(s.id));
	});
	const hiddenCount = $derived(risk_assessment.risk_scenarios.length - selectedScenarios.length);

	const modalStore: ModalStore = getModalStore();

	const user = page.data.user;
	const model = URL_MODEL_MAP['risk-assessments'];
	const canEditObject: boolean = canPerformActionOnObject({
		user,
		action: 'change',
		model: model.name,
		object: risk_assessment
	});
	function modalCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.scenarioCreateForm,
				model: data.scenarioModel,
				scopeFolder: data.risk_assessment.folder,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.addRiskScenario()
		};
		modalStore.trigger(modal);
	}

	function modalDuplicateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.riskAssessmentDuplicateForm,
				model: data.riskAssessmentModel,
				debug: false,
				duplicate: true,
				formAction: '?/duplicate'
			}
		};

		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.duplicateRiskAssessment()
		};
		modalStore.trigger(modal);
	}

	function modalRequestValidation(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.validationFlowForm,
				model: data.validationFlowModel,
				debug: false,
				invalidateAll: true,
				formAction: '/validation-flows?/create',
				onConfirm: async () => {
					await refreshAll();
				}
			}
		};

		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.requestValidation()
		};
		modalStore.trigger(modal);
	}

	let syncingToActionsIsLoading = $state(false);

	async function modalConfirmSyncToActions(id: string, action: string): Promise<void> {
		const riskScenariosSync = await fetch(`/risk-assessments/${page.params.id}/sync-to-actions`, {
			method: 'POST'
		}).then((response) => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error('Failed to fetch applied controls sync data');
			}
		});
		const schema = z.object({ reset_residual: z.boolean().default(false) });
		const modalComponent: ModalComponent = {
			ref: SyncToActionsRiskModal,
			props: {
				_form: defaults({ reset_residual: false }, zod(schema)),
				id,
				schema,
				debug: false,
				URLModel: 'risk-assessments',
				formAction: action,
				listProps: {
					items: riskScenariosSync.changes.map((scenario) =>
						m.riskScenarioSyncWithChanges({
							ref_id: scenario.ref_id,
							name: scenario.name,
							current_level: scenario.current_level.name,
							residual_level: scenario.residual_level.name
						})
					),
					message: m.theFollowingChangesWillBeApplied()
				}
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.syncToAppliedControls(),
			body: m.syncToAppliedControlsRiskAssessmentMessage({
				count: risk_assessment.risk_scenarios.length //change this
			}),
			response: (r: boolean) => {
				syncingToActionsIsLoading = r;
			}
		};
		modalStore.trigger(modal);
	}

	$effect(() => {
		if (syncingToActionsIsLoading === true && (form || form?.error))
			syncingToActionsIsLoading = false;
	});

	const buildRiskCluster = (
		scenarios: RiskScenario[],
		risk_matrix: RiskMatrix,
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

	const currentCluster = $derived(
		buildRiskCluster(selectedScenarios, risk_assessment.risk_matrix, 'current')
	);
	const residualCluster = $derived(
		buildRiskCluster(selectedScenarios, risk_assessment.risk_matrix, 'residual')
	);

	let fields = [
		'ref_id',
		'name',
		'threats',
		...(page.data?.featureflags?.inherent_risk ? ['inherent_level'] : []),
		'existing_applied_controls',
		'current_level',
		'within_tolerance',
		'applied_controls',
		'residual_level'
	];

	function buildExportGroups(selectionQuery: URLSearchParams): ExportGroup[] {
		const id = risk_assessment.id;
		// Same default as the action plan page: the measures still to implement.
		const actionPlanQuery = new URLSearchParams(selectionQuery);
		actionPlanQuery.set(LINK_TYPE_PARAM, DEFAULT_LINK_TYPE);
		return [
			{
				titleKey: 'riskAssessment',
				options: [
					{
						titleKey: 'exportRiskReport',
						descriptionKey: 'exportRiskReportDesc',
						format: 'PDF' as const,
						href: withParams(`/risk-assessments/${id}/export/pdf`, selectionQuery),
						testId: 'export-option-pdf'
					},
					{
						titleKey: 'exportRiskScenariosData',
						descriptionKey: 'exportRiskScenariosDataDesc',
						format: 'CSV' as const,
						href: withParams(`/risk-assessments/${id}/export/csv`, selectionQuery),
						testId: 'export-option-csv'
					},
					{
						titleKey: 'exportRiskScenariosWorkbook',
						descriptionKey: 'exportRiskScenariosWorkbookDesc',
						format: 'XLSX' as const,
						href: withParams(`/risk-assessments/${id}/export/xlsx`, selectionQuery),
						testId: 'export-option-xlsx'
					}
				]
			},
			{
				titleKey: 'actionPlan',
				options: [
					{
						titleKey: 'exportStatusGroupedReport',
						descriptionKey: 'exportStatusGroupedReportDesc',
						format: 'PDF' as const,
						href: withParams(`/risk-assessments/${id}/action-plan/export/pdf`, actionPlanQuery),
						testId: 'export-option-ap-pdf'
					},
					{
						titleKey: 'exportControlsWorkbook',
						descriptionKey: 'exportControlsWorkbookDesc',
						format: 'XLSX' as const,
						href: withParams(`/risk-assessments/${id}/action-plan/export/excel`, actionPlanQuery),
						testId: 'export-option-ap-xlsx'
					}
				]
			}
		];
	}

	function modalExport(): void {
		const modalComponent: ModalComponent = {
			ref: ExportModal,
			props: {
				title: m.exportOptionsTitle(),
				groups: buildExportGroups(new URLSearchParams()),
				selection:
					scoped && selection
						? {
								count: selection.count,
								total: selection.total,
								summary: selectionSummary(readSelection(page.url.searchParams), selection),
								groups: buildExportGroups(selectionQuery)
							}
						: undefined
			}
		};
		modalStore.trigger({ type: 'component', component: modalComponent });
	}
</script>

<main class="grow main">
	<div>
		{#if risk_assessment.is_locked}
			<div
				class="alert bg-yellow-100 border border-yellow-300 text-yellow-800 px-4 py-3 rounded-lg shadow-sm mx-4 mt-4"
			>
				<div class="flex items-center">
					<i class="fa-solid fa-lock text-yellow-600 mr-2"></i>
					<span class="font-medium">{m.lockedAssessment()}</span>
					<span class="ml-2 text-sm">{m.lockedAssessmentMessage()}</span>
				</div>
			</div>
		{/if}
		<div class="card bg-surface-50-950 p-4 m-4 shadow-sm flex flex-col lg:flex-row gap-4 relative">
			<div class="container lg:w-1/3">
				<div id="name" class="text-lg font-semibold" data-testid="name-field-value">
					{#if risk_assessment.perimeter}
						{risk_assessment.perimeter.str}/{risk_assessment.name} - {risk_assessment.version}
					{:else}
						{risk_assessment.folder.str}/{risk_assessment.name} - {risk_assessment.version}
					{/if}
				</div>
				<br />
				<div class="text-sm">
					<ul class="leading-loose">
						<li>
							<span class="font-semibold">{m.refId()}:</span>
							{risk_assessment.ref_id ?? '--'}
						</li>
						<li>
							<span class="font-semibold">{m.status()}:</span>
							{!risk_assessment.status ? '--' : safeTranslate(risk_assessment.status)}
						</li>
						<li>
							<span class="font-semibold">{m.authors()}:</span>
							<ul>
								{#each risk_assessment.authors as author}
									<li>{author.str}</li>
								{/each}
							</ul>
						</li>
						<li>
							<span class="font-semibold">{m.reviewers()}:</span>
							<ul>
								{#each risk_assessment.reviewers as reviewer}
									<li>{reviewer.str}</li>
								{/each}
							</ul>
						</li>
						<li>
							<span class="font-semibold">{m.createdAt()}:</span>
							{formatDate(new Date(risk_assessment.created_at), true, getLocale())}
						</li>
						<li>
							<span class="font-semibold">{m.updatedAt()}:</span>
							{formatDate(new Date(risk_assessment.updated_at), true, getLocale())}
						</li>
					</ul>
				</div>
				<br />
				{#if page.data?.featureflags?.validation_flows}
					{#key risk_assessment.validation_flows}
						<ValidationFlowsSection validationFlows={risk_assessment.validation_flows} />
					{/key}
				{/if}
			</div>
			<div class="container lg:w-2/3">
				<div class="text-sm">
					<span class="font-semibold" data-testid="risk-matrix-field-title">{m.riskMatrix()}:</span>
					<Anchor
						href="/risk-matrices/{risk_assessment.risk_matrix.id}"
						class="anchor"
						data-testid="risk-matrix-field-value">{risk_assessment.risk_matrix.name}</Anchor
					>
				</div>
				<br />
				{#if risk_assessment.ebios_rm_study}
					<div class="text-sm">
						<span class="font-semibold" data-testid="ebios-rm-field-title">{m.ebiosRmStudy()}:</span
						>
						<Anchor
							href="/ebios-rm/{risk_assessment.ebios_rm_study.id}"
							class="anchor"
							data-testid="ebios-rm-field-value">{risk_assessment.ebios_rm_study.name}</Anchor
						>
					</div>
					<br />
				{/if}
				<div class="text-sm">
					<span class="font-semibold" data-testid="description-field-title">{m.description()}:</span
					>
				</div>
				<div class="text-sm" data-testid="description-field-value">
					<MarkdownRenderer content={risk_assessment.description} />
				</div>
			</div>
			<div class="flex flex-col space-y-2 w-full lg:w-80 xl:w-96 shrink-0">
				<!-- Same pattern as the audit header: filled primary first, the rest quiet. -->
				<div class="action-grid">
					{#if canEditObject}
						<Anchor
							href="/risk-assessments/{risk_assessment.id}/edit?next=/risk-assessments/{risk_assessment.id}"
							label={m.edit()}
							class="btn preset-filled-primary-500"
							data-testid="edit-button"
						>
							<i class="fa-solid fa-edit mr-2"></i>
							{m.edit()}</Anchor
						>
					{/if}
					<button
						type="button"
						class="btn btn-quiet"
						onclick={modalExport}
						data-testid="export-button"
					>
						<i class="fa-solid fa-download mr-2 text-sky-500"></i>{m.exportButton()}
					</button>
					<Anchor
						label={m.actionPlan()}
						href={withParams(`/risk-assessments/${risk_assessment.id}/action-plan`, selectionQuery)}
						class="btn btn-quiet"
						data-testid="action-plan-button"
						><i class="fa-solid fa-heart-pulse mr-2 text-red-500"></i>{m.actionPlan()}
						{#if scoped && selection}
							<span class="badge preset-tonal-primary ml-2 text-xs">
								{m.scenarioCount({ count: selection.count })}
							</span>
						{/if}</Anchor
					>
					<Anchor
						label={m.analytics()}
						href="/risk-assessments/{risk_assessment.id}/analytics"
						class="btn btn-quiet"
						><i class="fa-solid fa-chart-line mr-2 text-indigo-500"></i>{m.analytics()}</Anchor
					>
					<Anchor
						label={m.riskTrajectory()}
						href="/risk-assessments/{risk_assessment.id}/trajectory"
						class="btn btn-quiet"
						><i class="fa-solid fa-route mr-2 text-teal-500"></i>{m.riskTrajectory()}</Anchor
					>
					<AuditTrailButton
						model="risk-assessments"
						objectId={risk_assessment.id}
						folderId={risk_assessment.folder?.id ?? user.root_folder_id}
					/>
				</div>
				<div class="pt-3 mt-1 border-t border-surface-200-800 space-y-1.5">
					<span
						class="text-xs font-semibold text-surface-400-600 uppercase tracking-widest select-none"
						>{m.powerUps()}</span
					>
				</div>
				<div class="grid grid-cols-2 gap-2">
					<button
						class="action-tile"
						onclick={(_) => modalDuplicateForm()}
						data-testid="duplicate-button"
					>
						<i class="fa-solid fa-copy text-fuchsia-500"></i>
						{m.duplicate()}</button
					>
					{#if !risk_assessment?.is_locked}
						<button
							class="action-tile"
							onclick={async () => {
								await modalConfirmSyncToActions(risk_assessment.id, '?/syncToActions');
							}}
						>
							<span>
								{#if syncingToActionsIsLoading}
									<Progress value={null}>
										<Progress.Circle class="[--size:--spacing(6)] -ml-2">
											<Progress.CircleTrack />
											<Progress.CircleRange class="stroke-current" />
										</Progress.Circle>
									</Progress>
								{:else}
									<i class="fa-solid fa-arrows-rotate text-cyan-500"></i>
								{/if}
							</span>
							{m.syncToAppliedControls()}
						</button>
					{/if}
					<Anchor
						href="/risk-assessments/{risk_assessment.id}/convert-to-quantitative"
						label={m.convertToQuantitative()}
						class="action-tile"
					>
						<i class="fa-solid fa-calculator text-yellow-600"></i>
						{m.convertToQuantitative()}
					</Anchor>
					{#if !risk_assessment?.is_locked && page.data?.featureflags?.validation_flows}
						<button
							class="action-tile"
							onclick={() => modalRequestValidation()}
							data-testid="request-validation-button"
						>
							<i class="fa-solid fa-check-circle text-amber-500"></i>
							{m.requestValidation()}
						</button>
					{/if}
				</div>
			</div>
		</div>
	</div>
	<div class="mx-4">
		<ScenarioSelectionBar riskAssessmentId={risk_assessment.id} {selection} />
		{#if data.selectionError}
			<p class="mt-2 text-sm text-error-600" role="alert">{m.selectionError()}</p>
		{/if}
	</div>
	<!--Risk risk_assessment-->
	<div class="card m-4 p-4 shadow-sm bg-surface-50-950">
		<div class="bg-surface-50-950">
			<div class="flex flex-row justify-between">
				<h4 class="text-lg font-semibold lowercase capitalize-first my-auto">
					{m.associatedRiskScenarios()}
				</h4>
			</div>
			<ModelTable
				source={data.scenariosTable}
				deleteForm={data.scenarioDeleteForm}
				model={getModelInfo('risk-scenarios')}
				URLModel="risk-scenarios"
				search={false}
				tableFilters={{}}
				baseEndpoint="/risk-scenarios?risk_assessment={risk_assessment.id}"
				extraParams={unprefixedSelection(page.url.searchParams).toString()}
				folderId={data.risk_assessment.folder.id}
				{fields}
				disableCreate={risk_assessment.is_locked}
				disableEdit={risk_assessment.is_locked}
				disableDelete={risk_assessment.is_locked}
			>
				{#snippet addButton()}
					{#if !risk_assessment.is_locked}
						<button
							class="btn preset-filled-primary-500 self-end my-auto"
							onclick={(_) => modalCreateForm()}
						>
							<i class="fa-solid fa-plus mr-2 lowercase"></i>
							{m.addRiskScenario()}
						</button>
					{/if}
				{/snippet}
			</ModelTable>
		</div>
	</div>
	<!--Matrix view-->
	<div class="card m-4 p-4 shadow-sm bg-surface-50-950 page-break">
		<div class="flex flex-wrap items-baseline justify-between gap-2">
			<div class="text-lg font-semibold">{m.riskMatrixView()}</div>
			{#if scoped && selection}
				<span
					class="inline-flex items-center gap-2 text-xs font-semibold rounded-full px-3 py-1 bg-primary-50 text-primary-700 dark:bg-primary-900/40 dark:text-primary-200"
					data-testid="matrix-selection-badge"
				>
					<i class="fa-solid fa-filter" aria-hidden="true"></i>
					{m.scenarioSelectionCount({ count: selection.count, total: selection.total })}
					<span class="font-normal">· {m.outsideSelectionHidden({ count: hiddenCount })}</span>
				</span>
			{/if}
		</div>
		<div class="flex flex-wrap justify-between gap-8 [&>div]:basis-xl [&>div]:grow">
			{#if page.data?.featureflags?.inherent_risk}
				<div>
					<h3 class="font-bold p-2 m-2 text-lg text-center">{m.inherentRisk()}</h3>

					<RiskMatrix
						riskMatrix={risk_assessment.risk_matrix}
						matrixName={'inherent'}
						data={buildRiskCluster(selectedScenarios, risk_assessment.risk_matrix, 'inherent')}
						dataItemComponent={RiskScenarioItem}
						{useBubbles}
					/>
				</div>
			{/if}
			<div>
				<h3 class="font-bold p-2 m-2 text-lg text-center">{m.currentRisk()}</h3>

				<RiskMatrix
					riskMatrix={risk_assessment.risk_matrix}
					matrixName={'current'}
					data={currentCluster}
					dataItemComponent={RiskScenarioItem}
					showLegend={showRisks}
					{useBubbles}
				/>
			</div>
			<div>
				<h3 class="font-bold p-2 m-2 text-lg text-center">{m.residualRisk()}</h3>

				<RiskMatrix
					riskMatrix={risk_assessment.risk_matrix}
					matrixName={'residual'}
					data={residualCluster}
					dataItemComponent={RiskScenarioItem}
					{useBubbles}
				/>
			</div>
		</div>
	</div>
</main>
