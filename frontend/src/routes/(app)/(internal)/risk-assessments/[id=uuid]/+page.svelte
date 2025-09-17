<script lang="ts">
	import { page } from '$app/state';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import RiskMatrix from '$lib/components/RiskMatrix/RiskMatrix.svelte';
	import { URL_MODEL_MAP, getModelInfo } from '$lib/utils/crud';
	import type { RiskMatrixJsonDefinition, RiskScenario } from '$lib/utils/types';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import RiskScenarioItem from '$lib/components/RiskMatrix/RiskScenarioItem.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { canPerformAction } from '$lib/utils/access-control';
	import { getLocale } from '$paraglide/runtime';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import { Popover, ProgressRing } from '@skeletonlabs/skeleton-svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import List from '$lib/components/List/List.svelte';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import SyncToActionsRiskModal from '$lib/components/Modals/SyncToActionsRiskModal.svelte';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';
	import z from 'zod';

	let { data, form } = $props();

	let exportPopupOpen = $state(false);

	const showRisks = true;
	const useBubbles = data.useBubbles;
	const risk_assessment = data.risk_assessment;

	const modalStore: ModalStore = getModalStore();

	const user = page.data.user;
	const model = URL_MODEL_MAP['risk-assessments'];
	const canEditObject: boolean = canPerformAction({
		user,
		action: 'change',
		model: model.name,
		domain: risk_assessment.folder.id
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

	const currentCluster = buildRiskCluster(
		risk_assessment.risk_scenarios,
		risk_assessment.risk_matrix,
		'current'
	);
	const residualCluster = buildRiskCluster(
		risk_assessment.risk_scenarios,
		risk_assessment.risk_matrix,
		'residual'
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
		<div class="card bg-white p-4 m-4 shadow-sm flex space-x-2 relative">
			<div class="container w-1/3">
				<div id="name" class="text-lg font-semibold" data-testid="name-field-value">
					{risk_assessment.perimeter.str}/{risk_assessment.name} - {risk_assessment.version}
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
							<span class="font-semibold">{m.createdAt()}:</span>
							{new Date(risk_assessment.created_at).toLocaleString(getLocale())}
						</li>
						<li>
							<span class="font-semibold">{m.updatedAt()}:</span>
							{new Date(risk_assessment.updated_at).toLocaleString(getLocale())}
						</li>
					</ul>
				</div>
			</div>
			<div class="container w-2/3">
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
			<div class="flex flex-col space-y-2 ml-4">
				<div class="flex flex-row space-x-2">
					<Popover
						open={exportPopupOpen}
						onOpenChange={(e) => (exportPopupOpen = e.open)}
						triggerClasses="btn preset-filled-primary-500 w-full"
					>
						{#snippet trigger()}
							<span data-testid="export-button">
								<i class="fa-solid fa-download mr-2"></i>{m.exportButton()}
							</span>
						{/snippet}
						{#snippet content()}
							<div class="card whitespace-nowrap bg-white py-2 w-fit shadow-lg space-y-1">
								<p class="block px-4 py-2 text-sm text-gray-800">{m.riskAssessment()}</p>
								<a
									href="/risk-assessments/{risk_assessment.id}/export/pdf"
									class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200">... {m.asPDF()}</a
								>
								<a
									href="/risk-assessments/{risk_assessment.id}/export/csv"
									class="block px-4 py-2 text-sm text-gray-800 border-b hover:bg-gray-200"
									>... {m.asCSV()}</a
								>
								<p class="block px-4 py-2 text-sm text-gray-800">{m.actionPlan()}</p>
								<a
									href="/risk-assessments/{risk_assessment.id}/action-plan/export/pdf"
									class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200">... {m.asPDF()}</a
								>
								<a
									href="/risk-assessments/{risk_assessment.id}/action-plan/export/excel"
									class="block px-4 py-2 text-sm text-gray-800 border-b hover:bg-gray-200"
									>... {m.asXLSX()}</a
								>
							</div>
						{/snippet}
					</Popover>
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
				</div>
				<Anchor
					label={m.actionPlan()}
					href="/risk-assessments/{risk_assessment.id}/action-plan"
					class="btn preset-filled-primary-500"
					><i class="fa-solid fa-heart-pulse mr-2"></i>{m.actionPlan()}</Anchor
				>
				<span class="pt-4 font-light text-sm">{m.powerUps()}</span>
				<button
					class="btn text-gray-100 bg-linear-to-l from-sky-500 to-green-600"
					onclick={(_) => modalDuplicateForm()}
					data-testid="duplicate-button"
				>
					<i class="fa-solid fa-copy mr-2"></i>
					{m.duplicate()}</button
				>
				{#if !risk_assessment?.is_locked}
					<button
						class="btn text-gray-100 bg-linear-to-r from-cyan-500 to-blue-500 h-fit"
						onclick={async () => {
							await modalConfirmSyncToActions(risk_assessment.id, '?/syncToActions');
						}}
					>
						<span class="mr-2">
							{#if syncingToActionsIsLoading}
								<ProgressRing
									strokeWidth="16px"
									meterStroke="stroke-white"
									size="size-6"
									classes="-ml-2"
								/>
							{:else}
								<i class="fa-solid fa-arrows-rotate mr-2"></i>
							{/if}
						</span>
						{m.syncToAppliedControls()}
					</button>
				{/if}
			</div>
		</div>
	</div>
	<!--Risk risk_assessment-->
	<div class="card m-4 p-4 shadow-sm bg-white">
		<div class="bg-white">
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
				baseEndpoint="/risk-scenarios?risk_assessment={risk_assessment.id}"
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
	<div class="card m-4 p-4 shadow-sm bg-white page-break">
		<div class="text-lg font-semibold">{m.riskMatrixView()}</div>
		<div class="flex flex-wrap justify-between gap-8 [&>div]:basis-xl [&>div]:grow">
			{#if page.data?.featureflags?.inherent_risk}
				<div>
					<h3 class="font-bold p-2 m-2 text-lg text-center">{m.inherentRisk()}</h3>

					<RiskMatrix
						riskMatrix={risk_assessment.risk_matrix}
						matrixName={'inherent'}
						data={buildRiskCluster(
							risk_assessment.risk_scenarios,
							risk_assessment.risk_matrix,
							'inherent'
						)}
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
					showLegend={showRisks}
					{useBubbles}
				/>
			</div>
		</div>
	</div>
</main>
