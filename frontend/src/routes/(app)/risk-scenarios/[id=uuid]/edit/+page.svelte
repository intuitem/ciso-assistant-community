<script lang="ts">
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { getOptions } from '$lib/utils/crud';
	import { modelSchema } from '$lib/utils/schemas';
	import { getSecureRedirect } from '$lib/utils/helpers';
	import {
		getModalStore,
		getToastStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore,
		type ToastStore
	} from '@skeletonlabs/skeleton';
	import type { PageData } from './$types';
	import type { StrengthOfKnowledgeEntry } from '$lib/utils/types';
	import RiskLevel from './RiskLevel.svelte';

	import { browser } from '$app/environment';
	import { breadcrumbObject } from '$lib/utils/stores';
	import { superForm } from 'sveltekit-superforms';
	import { page } from '$app/stores';

	import * as m from '$paraglide/messages';
	import { localItems, capitalizeFirstLetter, toCamelCase } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';
	import { zod } from 'sveltekit-superforms/adapters';

	export let data: PageData;

	breadcrumbObject.set(data.scenario);

	const schema = modelSchema(data.model.urlModel!);

	const strengthOfKnowledgeFormChoices: { label: string; value: number }[] = (
		Object.entries(data.strengthOfKnowledgeChoices) as StrengthOfKnowledgeEntry[]
	)
		.map(([key, value]) => ({
			label: value.name,
			value: parseInt(key)
		}))
		.sort((a, b) => a.value - b.value);

	const modalStore: ModalStore = getModalStore();
	const toastStore: ToastStore = getToastStore();

	function cancel(): void {
		if (browser) {
			var currentUrl = window.location.href;
			var url = new URL(currentUrl);
			var nextValue = getSecureRedirect(url.searchParams.get('next'));
			if (nextValue) window.location.href = nextValue;
		}
	}

	function modalMeasureCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.measureCreateForm,
				formAction: 'createAppliedControl',
				model: data.measureModel,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: localItems()['add' + capitalizeFirstLetter(data.measureModel.localName)]
		};
		modalStore.trigger(modal);
	}

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

	let { form: measureCreateForm, message: measureCreateMessage } = {
		form: {},
		message: {}
	};

	// NOTE: This is a workaround for an issue we had with getting the return value from the form actions after switching pages in route /[model=urlmodel]/ without a full page reload.
	// invalidateAll() did not work.
	$: {
		({ form: measureCreateForm, message: measureCreateMessage } = superForm(
			data.measureCreateForm,
			{
				onUpdated: ({ form }) =>
					handleFormUpdated({ form, pageStatus: $page.status, closeModal: true })
			}
		));
	}
	const next = getSecureRedirect($page.url.searchParams.get('next'));

	const probabilityColorMap = data.riskMatrix.probability.map(
		(probability) => probability.hexcolor
	);
	const impactColorMap = data.riskMatrix.impact.map((impact) => impact.hexcolor);
</script>

<div>
	<SuperForm
		class="flex flex-col space-y-3"
		data={data.form}
		dataType="json"
		let:form
		validators={zod(schema)}
		action="?/updateRiskScenario={next}"
		{...$$restProps}
	>
		<div class="flex flex-row space-x-2">
			<div class="card px-4 py-2 bg-white shadow-lg w-1/2">
				<h4 class="h4 font-semibold">{m.scope()}</h4>
				<div class="flex flex-row justify-between">
					<span>
						<p class="text-sm font-semibold text-gray-400">{m.project()}</p>
						<a class="anchor text-sm font-semibold" href="/projects/{data.scenario.project.id}"
							>{data.scenario.project.str}</a
						>
					</span>
					<AutocompleteSelect
						{form}
						options={getOptions({ objects: data.foreignKeys['risk_assessment'] })}
						field="risk_assessment"
						label={m.riskAssessment()}
					/>
					<span>
						<p class="text-sm font-semibold text-gray-400">{m.version()}</p>
						<p class="text-sm font-semibold">{data.scenario.version}</p>
					</span>
				</div>
			</div>
			<div class="card px-4 py-2 bg-white shadow-lg w-1/2">
				<h4 class="h4 font-semibold">{m.status()}</h4>
				<div class="flex flex-row justify-between">
					<div class="w-1/4">
						<p class="text-sm font-semibold text-gray-400">{m.lastUpdate()}</p>
						<p class="text-sm font-semibold">
							{new Date(data.scenario.updated_at).toLocaleString(languageTag())}
						</p>
					</div>
					<div class=" px-2 w-2/4">
						<AutocompleteSelect
							{form}
							multiple
							options={getOptions({ objects: data.foreignKeys['owner'], label: 'email' })}
							field="owner"
							label="Owner(s)"
						/>
					</div>
					<div class=" w-1/4">
						<Select
							{form}
							options={data.treatmentChoices}
							field="treatment"
							label={m.treatmentStatus()}
						/>
					</div>
				</div>
			</div>
		</div>

		<div class="flex flex-row space-x-2">
			<div class="card px-4 py-2 bg-white shadow-lg space-y-4 w-3/5">
				<AutocompleteSelect
					{form}
					multiple
					options={getOptions({ objects: data.foreignKeys['threats'] })}
					field="threats"
					label={m.threats()}
				/>
				<TextField {form} field="name" label={m.name()} />
				<TextArea {form} field="description" label={m.description()} />
			</div>
			<div class="card px-4 py-2 bg-white shadow-lg w-2/5 max-h-96 overflow-y-scroll">
				<AutocompleteSelect
					multiple
					{form}
					options={getOptions({ objects: data.foreignKeys['assets'] })}
					field="assets"
					label={m.assets()}
					helpText={m.riskScenarioAssetHelpText()}
				/>
				<ModelTable source={data.tables['assets']} hideFilters={true} URLModel="assets" />
			</div>
		</div>
		<input type="hidden" name="urlmodel" value={data.model.urlModel} />

		<div class="card px-4 py-2 bg-white shadow-lg">
			<h4 class="h4 font-semibold">{m.currentRisk()}</h4>
			<div class="flex flex-row space-x-4 justify-between">
				<TextArea
					{form}
					field="existing_controls"
					label={m.existingControls()}
					helpText={m.riskScenarioMeasureHelpText()}
					regionContainer="w-1/2"
				/>
				<div class="flex flex-col">
					<h5 class="h5 font-medium">{m.currentAssessment()}</h5>
					<div class="flex flex-row space-x-4 my-auto">
						<Select
							{form}
							options={data.probabilityChoices}
							color_map={probabilityColorMap}
							field="current_proba"
							label={m.currentProba()}
						/>
						<i class="fa-solid fa-xmark mt-8" />
						<Select
							{form}
							options={data.impactChoices}
							color_map={impactColorMap}
							field="current_impact"
							label={m.currentImpact()}
						/>
						<i class="fa-solid fa-equals mt-8" />
						<RiskLevel
							{form}
							field="current_risk_level"
							label={m.currentRiskLevel()}
							riskMatrix={data.riskMatrix}
							probabilityField="current_proba"
							impactField="current_impact"
							helpText={m.currentRiskLevelHelpText()}
						/>
					</div>
				</div>
			</div>
		</div>

		<div class="card px-4 py-2 bg-white shadow-lg">
			<h4 class="h4 font-semibold">{m.residualRisk()}</h4>
			<div class="flex flex-row space-x-4 justify-between">
				<div class="flex flex-col space-y-4 w-1/2">
					<span class="flex flex-row justify-between items-center">
						<h5 class="h5 font-medium">{m.associatedAppliedControls()}</h5>
						<button
							class="btn variant-filled-primary self-end"
							on:click={modalMeasureCreateForm}
							type="button"><i class="fa-solid fa-plus mr-2" />{m.addAppliedControl()}</button
						>
					</span>
					<AutocompleteSelect
						multiple
						{form}
						options={getOptions({ objects: data.foreignKeys['applied_controls'] })}
						field="applied_controls"
						label={m.appliedControls()}
					/>
					<ModelTable
						source={data.tables['applied-controls']}
						hideFilters={true}
						URLModel="applied-controls"
					/>
				</div>
				<div class="flex flex-col">
					<h5 class="h5 font-medium">{m.targetAssessment()}</h5>
					<div class="flex flex-row space-x-4 my-auto">
						<Select
							{form}
							options={data.probabilityChoices}
							color_map={probabilityColorMap}
							field="residual_proba"
							label={m.residualProba()}
						/>
						<i class="fa-solid fa-xmark mt-8" />
						<Select
							{form}
							options={data.impactChoices}
							color_map={impactColorMap}
							field="residual_impact"
							label={m.residualImpact()}
						/>
						<i class="fa-solid fa-equals mt-8" />
						<RiskLevel
							{form}
							field="current_risk_level"
							label={m.residualRiskLevel()}
							riskMatrix={data.riskMatrix}
							probabilityField="residual_proba"
							impactField="residual_impact"
							helpText={m.residualRiskLevelHelpText()}
						/>
					</div>
				</div>
			</div>
		</div>
		<div class="card px-4 py-2 bg-white shadow-lg">
			<Select
				{form}
				options={data.qualificationChoices}
				field="qualification"
				label={m.qualificationStatus()}
			/>
			<Select
				{form}
				options={strengthOfKnowledgeFormChoices}
				field="strength_of_knowledge"
				label={m.strengthOfKnowledge()}
			/>
			<TextArea {form} field="justification" label={m.justification()} />
		</div>
		<div class="flex flex-row justify-between space-x-4">
			<button
				class="btn bg-gray-400 text-white font-semibold w-full"
				data-testid="cancel-button"
				type="button"
				on:click={cancel}>{m.cancel()}</button
			>
			<button class="btn variant-filled-primary font-semibold w-full" data-testid="save-button"
				>{m.save()}</button
			>
		</div>
	</SuperForm>
</div>
