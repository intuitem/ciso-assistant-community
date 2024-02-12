<script lang="ts">
	import type { RiskScenario, RiskMatrixJsonDefinition } from '$lib/utils/types';
	import type {
		ModalComponent,
		ModalSettings,
		ModalStore,
		ToastStore
	} from '@skeletonlabs/skeleton';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import RiskMatrix from '$lib/components/RiskMatrix/RiskMatrix.svelte';
	import type { PopupSettings } from '@skeletonlabs/skeleton';
	import { popup } from '@skeletonlabs/skeleton';
	import { getModalStore, getToastStore } from '@skeletonlabs/skeleton';
	import { breadcrumbObject } from '$lib/utils/stores';
	import { superForm } from 'sveltekit-superforms/client';
	import { page } from '$app/stores';
	import { URL_MODEL_MAP } from '$lib/utils/crud.js';

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

	function getForms(model: Record<string, any>) {
		let { form: createForm, message: createMessage } = superForm(model.createForm, {
			onUpdated: ({ form }) =>
				handleFormUpdated({ form, pageStatus: $page.status, closeModal: true })
		});
		let { form: deleteForm, message: deleteMessage } = superForm(model.deleteForm, {
			onUpdated: ({ form }) =>
				handleFormUpdated({ form, pageStatus: $page.status, closeModal: true })
		});
		return { createForm, createMessage, deleteForm, deleteMessage };
	}

	let forms = {};

	$: Object.entries(data.relatedModels).forEach(([key, value]) => {
		forms[key] = getForms(value);
	});

	function modalCreateForm(model: Record<string, any>): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: model.createForm,
				model: model,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: `New ${model.info.verboseName.toLowerCase()}`
		};
		modalStore.trigger(modal);
	}

	const riskMap = (scenarios: RiskScenario[], risk_matrix: RiskMatrix) => {
		const parsedRiskMatrix: RiskMatrixJsonDefinition = JSON.parse(risk_matrix.json_definition);
		return scenarios.map((s) => {
			const currentImpact = parsedRiskMatrix.impact.findIndex(
				(e) => e.name === s.current_impact.toString()
			);
			const currentProbability = parsedRiskMatrix.probability.findIndex(
				(e) => e.name === s.current_proba.toString()
			);
			const residualImpact = parsedRiskMatrix.impact.findIndex(
				(e) => e.name === s.residual_impact.toString()
			);
			const residualProbability = parsedRiskMatrix.probability.findIndex(
				(e) => e.name === s.residual_proba.toString()
			);
			return {
				...s,
				current_impact: { label: s.current_impact, value: currentImpact },
				current_proba: { label: s.current_proba, value: currentProbability },
				residual_impact: { label: s.residual_impact, value: residualImpact },
				residual_proba: { label: s.residual_proba, value: residualProbability }
			};
		});
	};

	const buildRiskCluster = (
		_scenarios: RiskScenario[],
		risk_matrix: RiskMatrix,
		risk: 'current' | 'residual'
	) => {
		const parsedRiskMatrix: RiskMatrixJsonDefinition = JSON.parse(risk_matrix.json_definition);
		const scenarios = riskMap(_scenarios, risk_matrix);
		const grid: string[][][] = Array.from({ length: parsedRiskMatrix.probability.length }, () =>
			Array.from({ length: parsedRiskMatrix.impact.length }, () => [])
		);
		scenarios.forEach((scenario: RiskScenario, index: number) => {
			const probability = scenario[`${risk}_proba`].value;
			const impact = scenario[`${risk}_impact`].value;
			probability >= 0 && impact >= 0
				? grid[probability][impact].push(`R.${index + 1}`)
				: undefined;
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
			<div class="absolute right-2 top-2 py-2 px-4">
				<a href="/risk-assessments/{risk_assessment.id}/plan" class="btn variant-filled-primary" data-testid="edit-button"
					><i class="fa-solid fa-heart-pulse mr-2" />Remediation plan</a
				>
				<button class="btn variant-filled-primary" use:popup={popupDownload}
					><i class="fa-solid fa-download mr-2" />Export</button
				>
				<div
					class="card whitespace-nowrap bg-white py-2 w-fit shadow-lg space-y-1"
					data-popup="popupDownload"
				>
					<p class="block px-4 py-2 text-sm text-gray-800">Risk assessment</p>
					<a
						href="/risk-assessments/{risk_assessment.id}/export/pdf"
						class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200">... as PDF</a
					>
					<a
						href="/risk-assessments/{risk_assessment.id}/export/csv"
						class="block px-4 py-2 text-sm text-gray-800 border-b hover:bg-gray-200">... as csv</a
					>
					<p class="block px-4 py-2 text-sm text-gray-800">Treatment plan</p>
					<a
						href="/risk-assessments/{risk_assessment.id}/plan/export/pdf"
						class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200">... as PDF</a
					>
					<a
						href="/risk-assessments/{risk_assessment.id}/plan/export/csv"
						class="block px-4 py-2 text-sm text-gray-800 border-b hover:bg-gray-200">... as csv</a
					>
				</div>
				{#if canEditObject}
					<a
						href="/risk-assessments/{risk_assessment.id}/edit?next=/risk-assessments/{risk_assessment.id}"
						class="btn variant-filled-primary"
						data-testid="edit-button"
					>
						<i class="fa-solid fa-edit mr-2" />
						Edit</a
					>
				{/if}
			</div>
			<div class="container w-1/3">
				<div id="name" class="text-lg font-semibold" data-testid="name-field-value">
					{#if risk_assessment.is_draft}
						<span class="badge bg-blue-200">Draft</span>
					{/if}
					{risk_assessment.project.str}/{risk_assessment.name} - {risk_assessment.version}
				</div>
				<br />
				<div class="text-sm">
					<ul>
						<li class="pb-1">
							<span class="font-semibold">Audited by:</span>
							{risk_assessment.auditor ? risk_assessment.auditor.str : '-'}
						</li>
						<li class="pb-1">
							<span class="font-semibold">Created at:</span>
							{new Date(risk_assessment.created_at).toLocaleString()}
						</li>
						<li class="pb-1">
							<span class="font-semibold">Updated at:</span>
							{new Date(risk_assessment.updated_at).toLocaleString()}
						</li>
					</ul>
				</div>
			</div>
			<div class="container w-2/3">
				<div class="text-sm">
					<span class="font-semibold">Risk matrix:</span>
					<a href="/risk-matrices/{risk_assessment.risk_matrix.id}" class="anchor" data-testid="risk-matrix-field-value"
						>{risk_assessment.risk_matrix.name}</a
					>
				</div>
				<br />
				<div class="text-sm"><span class="font-semibold" data-testid="description-field-title">Description:</span></div>
				<div class="text-sm" data-testid="description-field-value">{risk_assessment.description ?? '-'}</div>
			</div>
		</div>
	</div>
	<!--Risk risk_assessment-->
	<div class="card m-4 p-4 shadow bg-white">
		{#if data.relatedModels}
			{#each Object.entries(data.relatedModels) as [urlmodel, model]}
				<div class="bg-white">
					<div class="flex flex-row justify-between">
						<h4 class="text-lg font-semibold lowercase capitalize-first my-auto">
							Associated {model.info.verboseNamePlural}
						</h4>
					</div>
					{#if model.table}
						<ModelTable source={model.table} deleteForm={model.deleteForm} URLModel={urlmodel}>
							<button
								slot="addButton"
								class="btn variant-filled-primary self-end my-auto"
								on:click={(_) => modalCreateForm(model)}
								><i class="fa-solid fa-plus mr-2 lowercase" />New {model.info.verboseName}</button
							>
						</ModelTable>
					{/if}
				</div>
			{/each}
		{/if}
	</div>
	<!--Matrix view-->
	<div class="card m-4 p-4 shadow bg-white page-break">
		<div class="text-lg font-semibold">Risk matrix view</div>
		<div class="flex space-x-3">
			<div class="w-1/2 p-6">
				<h3 class="font-bold p-2 m-2 text-lg">Current</h3>

				<RiskMatrix
					riskMatrix={risk_assessment.risk_matrix}
					{showRisks}
					data={currentCluster}
					wrapperClass="mt-8"
				/>
			</div>
			<div class="w-1/2 p-6">
				<h3 class="font-bold p-2 m-2 text-lg">Residual</h3>

				<RiskMatrix
					riskMatrix={risk_assessment.risk_matrix}
					data={residualCluster}
					wrapperClass="mt-8"
				/>
			</div>
		</div>
	</div>
</main>
