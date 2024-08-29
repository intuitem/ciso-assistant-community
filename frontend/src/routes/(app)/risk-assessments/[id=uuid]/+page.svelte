<script lang="ts">
	import { page } from '$app/stores';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import RiskMatrix from '$lib/components/RiskMatrix/RiskMatrix.svelte';
	import { URL_MODEL_MAP, getModelInfo } from '$lib/utils/crud.js';
	import { breadcrumbObject } from '$lib/utils/stores';
	import type { RiskMatrixJsonDefinition, RiskScenario } from '$lib/utils/types';
	import type {
		ModalComponent,
		ModalSettings,
		ModalStore,
		PopupSettings,
		ToastStore
	} from '@skeletonlabs/skeleton';
	import { getModalStore, getToastStore, popup } from '@skeletonlabs/skeleton';
	import { superForm } from 'sveltekit-superforms';

	import RiskScenarioItem from '$lib/components/RiskMatrix/RiskScenarioItem.svelte';
	import * as m from '$paraglide/messages';
	import { languageTag } from '$paraglide/runtime';
	import { localItems, toCamelCase } from '$lib/utils/locales.js';

	export let data;
	const showRisks = true;
	const risk_assessment = data.risk_assessment;

	breadcrumbObject.set(risk_assessment);

	const modalStore: ModalStore = getModalStore();
	const toastStore: ToastStore = getToastStore();

	const user = $page.data.user;
	const model = URL_MODEL_MAP['risk-assessments'];
	const canEditObject: boolean = Object.hasOwn(user.permissions, `change_${model.name}`);

	function handleFormUpdated({
		form,
		pageStatus,
		closeModal
	}: {
		form: any;
		pageStatus: number;
		closeModal: boolean;
	}) {
		if (closeModal && form.valid) {
			$modalStore[0] ? modalStore.close() : null;
		}
		if (form.message) {
			const toast: { message: string; background: string } = {
				message: form.message,
				background: pageStatus === 200 ? 'variant-filled-success' : 'variant-filled-error'
			};
			toastStore.trigger(toast);
		}
	}

	let { form: deleteForm, message: deleteMessage } = {
		form: {},
		message: {}
	};

	let { form: createForm, message: createMessage } = {
		form: {},
		message: {}
	};

	// NOTE: This is a workaround for an issue we had with getting the return value from the form actions after switching pages in route /[model=urlmodel]/ without a full page reload.
	// invalidateAll() did not work.
	$: {
		({ form: createForm, message: createMessage } = superForm(data.scenarioCreateForm, {
			onUpdated: ({ form }) =>
				handleFormUpdated({ form, pageStatus: $page.status, closeModal: true })
		}));
		({ form: deleteForm, message: deleteMessage } = superForm(data.scenarioDeleteForm, {
			onUpdated: ({ form }) =>
				handleFormUpdated({ form, pageStatus: $page.status, closeModal: true })
		}));
	}

	function modalCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.scenarioCreateForm,
				model: data.scenarioModel,
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
				riskAssessmentDuplication: true,
				formAction: 'duplicate'
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

	const buildRiskCluster = (
		scenarios: RiskScenario[],
		risk_matrix: RiskMatrix,
		risk: 'current' | 'residual'
	) => {
		const parsedRiskMatrix: RiskMatrixJsonDefinition = JSON.parse(risk_matrix.json_definition);
		const grid: unknown[][][] = Array.from({ length: parsedRiskMatrix.probability.length }, () =>
			Array.from({ length: parsedRiskMatrix.impact.length }, () => [])
		);
		scenarios.forEach((scenario: RiskScenario) => {
			const probability = scenario[`${risk}_proba`].value;
			const impact = scenario[`${risk}_impact`].value;
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

	const popupDownload: PopupSettings = {
		event: 'click',
		target: 'popupDownload',
		placement: 'bottom'
	};
</script>

<main class="flex-grow main">
	<div>
		<div class="card bg-white p-4 m-4 shadow flex space-x-2 relative">
			<div class="container w-1/3">
				<div id="name" class="text-lg font-semibold" data-testid="name-field-value">
					{risk_assessment.project.str}/{risk_assessment.name} - {risk_assessment.version}
				</div>
				<br />
				<div class="text-sm">
					<ul>
						<li class="pb-1">
							<span class="font-semibold">{m.status()}:</span>
							{risk_assessment.status === null
								? '--'
								: localItems()[toCamelCase(risk_assessment.status)]}
						</li>
						<li class="pb-1">
							<span class="font-semibold">{m.authors()}:</span>
							<ul>
								{#each risk_assessment.authors as author}
									<li>{author.str}</li>
								{/each}
							</ul>
						</li>
						<li class="pb-1">
							<span class="font-semibold">{m.createdAt()}:</span>
							{new Date(risk_assessment.created_at).toLocaleString(languageTag())}
						</li>
						<li class="pb-1">
							<span class="font-semibold">{m.updatedAt()}:</span>
							{new Date(risk_assessment.updated_at).toLocaleString(languageTag())}
						</li>
					</ul>
				</div>
			</div>
			<div class="container w-2/3">
				<div class="text-sm">
					<span class="font-semibold" data-testid="risk-matrix-field-title">{m.riskMatrix()}:</span>
					<a
						href="/risk-matrices/{risk_assessment.risk_matrix.id}"
						class="anchor"
						data-testid="risk-matrix-field-value">{risk_assessment.risk_matrix.name}</a
					>
				</div>
				<br />
				<div class="text-sm">
					<span class="font-semibold" data-testid="description-field-title">{m.description()}:</span
					>
				</div>
				<div class="text-sm" data-testid="description-field-value">
					{risk_assessment.description ?? '-'}
				</div>
			</div>
			<div class="flex flex-col space-y-2 ml-4">
				<div class="flex flex-row space-x-2">
					<button class="btn variant-filled-primary w-full" use:popup={popupDownload}
						><i class="fa-solid fa-download mr-2" />{m.exportButton()}</button
					>
					<div
						class="card whitespace-nowrap bg-white py-2 w-fit shadow-lg space-y-1"
						data-popup="popupDownload"
					>
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
						<p class="block px-4 py-2 text-sm text-gray-800">{m.treatmentPlan()}</p>
						<a
							href="/risk-assessments/{risk_assessment.id}/remediation-plan/export/pdf"
							class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200">... {m.asPDF()}</a
						>
						<a
							href="/risk-assessments/{risk_assessment.id}/remediation-plan/export/csv"
							class="block px-4 py-2 text-sm text-gray-800 border-b hover:bg-gray-200"
							>... {m.asCSV()}</a
						>
					</div>
					{#if canEditObject}
						<a
							href="/risk-assessments/{risk_assessment.id}/edit?next=/risk-assessments/{risk_assessment.id}"
							class="btn variant-filled-primary"
							data-testid="edit-button"
						>
							<i class="fa-solid fa-edit mr-2" />
							{m.edit()}</a
						>
					{/if}
				</div>
				<a
					href="/risk-assessments/{risk_assessment.id}/remediation-plan"
					class="btn variant-filled-primary"
					><i class="fa-solid fa-heart-pulse mr-2" />{m.remediationPlan()}</a
				>
				<span class="pt-4 font-light text-sm">Power-ups:</span>
				<button
					class="btn text-gray-100 bg-gradient-to-l from-sky-500 to-green-600"
					on:click={(_) => modalDuplicateForm()}
					data-testid="duplicate-button"
				>
					<i class="fa-solid fa-copy mr-2"></i>
					{m.duplicate()}</button
				>
			</div>
		</div>
	</div>
	<!--Risk risk_assessment-->
	<div class="card m-4 p-4 shadow bg-white">
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
			>
				<button
					slot="addButton"
					class="btn variant-filled-primary self-end my-auto"
					on:click={(_) => modalCreateForm()}
					><i class="fa-solid fa-plus mr-2 lowercase" />
					{m.addRiskScenario()}
				</button>
			</ModelTable>
		</div>
	</div>
	<!--Matrix view-->
	<div class="card m-4 p-4 shadow bg-white page-break">
		<div class="text-lg font-semibold">{m.riskMatrixView()}</div>
		<div class="flex flex-col xl:flex-row xl:space-x-4 justify-between">
			<div class="flex-1">
				<h3 class="font-bold p-2 m-2 text-lg text-center">{m.currentRisk()}</h3>

				<RiskMatrix
					riskMatrix={risk_assessment.risk_matrix}
					data={currentCluster}
					dataItemComponent={RiskScenarioItem}
					{showRisks}
				/>
			</div>
			<div class="flex-1">
				<h3 class="font-bold p-2 m-2 text-lg text-center">{m.residualRisk()}</h3>

				<RiskMatrix
					riskMatrix={risk_assessment.risk_matrix}
					data={residualCluster}
					dataItemComponent={RiskScenarioItem}
					{showRisks}
				/>
			</div>
		</div>
	</div>
</main>
