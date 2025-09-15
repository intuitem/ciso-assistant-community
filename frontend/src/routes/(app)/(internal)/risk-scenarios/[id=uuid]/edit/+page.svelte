<script lang="ts">
	import { run } from 'svelte/legacy';

	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { getSecureRedirect } from '$lib/utils/helpers';
	import { modelSchema } from '$lib/utils/schemas';
	import type { StrengthOfKnowledgeEntry } from '$lib/utils/types';
	import type { PageData, ActionData } from './$types';
	import RiskLevel from './RiskLevel.svelte';

	import { browser } from '$app/environment';
	import { page } from '$app/state';

	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { zod } from 'sveltekit-superforms/adapters';
	import { superForm } from 'sveltekit-superforms/client';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form = $bindable() }: Props = $props();

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

	function cancel(): void {
		if (browser) {
			var currentUrl = window.location.href;
			var url = new URL(currentUrl);
			var nextValue = getSecureRedirect(url.searchParams.get('next'));
			if (nextValue) window.location.href = nextValue;
		}
	}

	const _form = superForm(data.form, {
		dataType: 'json',
		invalidateAll: true,
		applyAction: true,
		resetForm: false,
		validators: zod(schema),
		taintedMessage: m.taintedFormMessage(),
		validationMethod: 'auto'
	});

	function modalMeasureCreateForm(field: string): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.measureCreateForm,
				formAction: '?/createAppliedControl&field=' + field,
				model: data.measureModel,
				invalidateAll: false,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: safeTranslate('add-' + data.measureModel.localName)
		};
		modalStore.trigger(modal);
	}

	let refreshKey = $state(false);
	run(() => {
		if (form?.newControl) {
			refreshKey = !refreshKey;
			_form.form.update((current: Record<string, any>) =>
				form?.newControl?.field
					? {
							...current,
							[form?.newControl?.field]: [
								...current[form?.newControl?.field],
								form?.newControl?.appliedControl
							]
						}
					: current
			);
			form = null;
		}
	});

	const next = getSecureRedirect(page.url.searchParams.get('next'));

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
		{_form}
		validators={zod(schema)}
		action="?/updateRiskScenario&next={next}"
	>
		<div class="flex flex-row space-x-2">
			<div class="card p-2 bg-white shadow-lg w-1/2">
				<div class="flex justify-between p-2">
					<div>
						<p class="text-sm font-semibold text-gray-400">{m.perimeter()}</p>
						<Anchor
							class="anchor text-sm font-semibold"
							href="/perimeters/{data.scenario.perimeter.id}">{data.scenario.perimeter.str}</Anchor
						>
					</div>
					<div>
						<p class="text-sm font-semibold text-gray-400">{m.riskAssessment()}</p>
						<Anchor
							class="anchor text-sm font-semibold"
							href="/risk-assessments/{data.scenario.risk_assessment.id}"
							>{data.scenario.risk_assessment.name} {data.scenario.version}</Anchor
						>
					</div>
					<div>
						<p class="text-sm font-semibold text-gray-400">{m.riskMatrix()}</p>
						<Anchor
							class="anchor text-sm font-semibold"
							href="/risk-matrices/{data.scenario.risk_matrix.id}"
							target="_blank"
							rel="noopener noreferrer">{data.scenario.risk_matrix.str}</Anchor
						>
					</div>
				</div>
			</div>
			<div class="card px-4 py-2 bg-white shadow-lg w-1/2">
				<div class="flex flex-row justify-between items-stretch">
					<div class=" px-2 w-2/3">
						<AutocompleteSelect
							form={_form}
							baseClass="flex-1"
							multiple
							optionsEndpoint="users?is_third_party=false"
							optionsLabelField="email"
							field="owner"
							label={m.owner()}
						/>
					</div>
					<div class="w-1/3">
						<Select
							class="flex-1"
							form={_form}
							options={data.treatmentChoices}
							field="treatment"
							label={m.treatmentStatus()}
						/>
					</div>
				</div>
			</div>
		</div>

		<div class="flex flex-row space-x-2 min-h-72">
			<div class="card px-4 py-2 bg-white shadow-lg space-y-4 w-5/12">
				<span class="flex flex-row space-x-2">
					<TextField form={_form} field="ref_id" label={m.refId()} />
					<TextField form={_form} field="name" label={m.name()} classesContainer="w-full" />
				</span>
				<TextArea form={_form} field="description" rows={6} label={m.description()} />
			</div>
			<div class="card px-4 py-2 bg-white shadow-lg w-7/12 max-h-96 overflow-y-auto">
				<AutocompleteSelect
					multiple
					form={_form}
					optionsEndpoint="assets"
					optionsLabelField="auto"
					optionsExtraFields={[['folder', 'str']]}
					optionsInfoFields={{
						fields: [
							{
								field: 'type'
							}
						],
						classes: 'text-blue-500'
					}}
					field="assets"
					optionsDetailedUrlParameters={[
						['scope_folder_id', page.data.scenario.perimeter.folder.id]
					]}
					label={m.assets()}
				/>
				<AutocompleteSelect
					form={_form}
					multiple
					optionsEndpoint="threats"
					optionsDetailedUrlParameters={[
						['scope_folder_id', page.data.scenario.perimeter.folder.id]
					]}
					optionsExtraFields={[['folder', 'str']]}
					optionsLabelField="auto"
					field="threats"
					label={m.threats()}
				/>
				<AutocompleteSelect
					multiple
					form={_form}
					optionsEndpoint="vulnerabilities"
					optionsDetailedUrlParameters={[
						['scope_folder_id', page.data.scenario.perimeter.folder.id]
					]}
					optionsExtraFields={[['folder', 'str']]}
					field="vulnerabilities"
					label={m.vulnerabilities()}
				/>
				<AutocompleteSelect
					multiple
					form={_form}
					optionsEndpoint="security-exceptions"
					optionsExtraFields={[['folder', 'str']]}
					field="security_exceptions"
					label={m.securityExceptions()}
				/>
			</div>
		</div>
		<input type="hidden" name="urlmodel" value={data.model.urlModel} />

		{#if page.data?.featureflags?.inherent_risk}
			<div class="card px-4 py-2 bg-white shadow-lg">
				<h4 class="h4 font-black mb-2">{m.inherentRisk()}</h4>
				<div class="flex flex-row space-x-8 justify-between">
					<div class="flex w-1/2">
						<div class="flex flex-row space-x-4 my-auto">
							<div class="min-w-36">
								<Select
									form={_form}
									options={data.probabilityChoices}
									color_map={probabilityColorMap}
									field="inherent_proba"
									label={m.inherentProba()}
								/>
							</div>
							<i class="fa-solid fa-xmark mt-8"></i>
							<div class="min-w-36">
								<Select
									form={_form}
									options={data.impactChoices}
									color_map={impactColorMap}
									field="inherent_impact"
									label={m.inherentImpact()}
								/>
							</div>
							<i class="fa-solid fa-equals mt-8"></i>
							<div class="min-w-38">
								<RiskLevel
									form={_form}
									field="inherent_risk_level"
									label={m.inherentRiskLevel()}
									riskMatrix={data.riskMatrix}
									probabilityField="inherent_proba"
									impactField="inherent_impact"
									helpText={m.inherentRiskLevelHelpText()}
								/>
							</div>
						</div>
					</div>
				</div>
			</div>
		{/if}

		<div class="card px-4 py-2 bg-white shadow-lg">
			<h4 class="h4 font-black mb-2">{m.currentRisk()}</h4>
			<div class="flex flex-row space-x-8 justify-between">
				<div class="w-1/2">
					<div class="flex mb-2">
						<div class="w-full mr-2">
							{#key refreshKey}
								<AutocompleteSelect
									multiple
									form={_form}
									optionsEndpoint="applied-controls"
									optionsExtraFields={[['folder', 'str']]}
									optionsDetailedUrlParameters={[
										['scope_folder_id', page.data.scenario.perimeter.folder.id]
									]}
									field="existing_applied_controls"
									label={m.existingControls()}
									helpText={m.existingControlsHelper()}
								/>
							{/key}
						</div>
						<div class="flex items-center justify-center">
							<div class="">
								<button
									class="btn bg-gray-300 h-10 w-10"
									onclick={(_) => modalMeasureCreateForm('existing_applied_controls')}
									type="button"><i class="fa-solid fa-plus text-sm"></i></button
								>
							</div>
						</div>
					</div>
				</div>
				<div class="flex w-1/2">
					<div>
						<div class="text-xs text-slate-500 mb-4">
							<i class="fa-solid fa-circle-info"></i>
							{m.riskOptionHelper()}
						</div>
						<div class="flex flex-row space-x-4 my-auto">
							<div class="min-w-36">
								<Select
									form={_form}
									options={data.probabilityChoices}
									color_map={probabilityColorMap}
									field="current_proba"
									label={m.currentProba()}
								/>
							</div>
							<i class="fa-solid fa-xmark mt-8"></i>
							<div class="min-w-36">
								<Select
									form={_form}
									options={data.impactChoices}
									color_map={impactColorMap}
									field="current_impact"
									label={m.currentImpact()}
								/>
							</div>
							<i class="fa-solid fa-equals mt-8"></i>
							<div class="min-w-38">
								<RiskLevel
									form={_form}
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
			</div>
		</div>

		<div class="card px-4 py-2 bg-white shadow-lg">
			<h4 class="h4 font-black mb-2">{m.residualRisk()}</h4>
			<div class="flex flex-row space-x-8">
				<div class="w-1/2">
					<div class="flex">
						<div class="w-full mr-2">
							{#key refreshKey}
								<AutocompleteSelect
									multiple
									form={_form}
									optionsEndpoint="applied-controls"
									optionsExtraFields={[['folder', 'str']]}
									optionsDetailedUrlParameters={[
										['scope_folder_id', page.data.scenario.perimeter.folder.id]
									]}
									field="applied_controls"
									label={m.extraAppliedControls()}
									helpText={m.extraControlsHelper()}
								/>
							{/key}
						</div>
						<div class="flex items-center justify-center">
							<div class="">
								<button
									class="btn bg-gray-300 h-10 w-10"
									onclick={(_) => modalMeasureCreateForm('applied_controls')}
									type="button"><i class="fa-solid fa-plus text-sm"></i></button
								>
							</div>
						</div>
					</div>
				</div>
				<div class="flex w-1/2">
					<div class="flex flex-row space-x-4 my-auto">
						<div class="min-w-36">
							<Select
								form={_form}
								options={data.probabilityChoices}
								color_map={probabilityColorMap}
								field="residual_proba"
								label={m.residualProba()}
							/>
						</div>
						<i class="fa-solid fa-xmark mt-8"></i>
						<div class="min-w-36">
							<Select
								form={_form}
								options={data.impactChoices}
								color_map={impactColorMap}
								field="residual_impact"
								label={m.residualImpact()}
							/>
						</div>
						<i class="fa-solid fa-equals mt-8"></i>
						<div class="min-w-38">
							<RiskLevel
								form={_form}
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
		</div>

		<div class="card px-4 py-2 bg-white shadow-lg">
			<div class="flex space-x-4 mb-1">
				<div class="w-1/2">
					<AutocompleteSelect
						form={_form}
						multiple
						optionsEndpoint="terminologies?field_path=qualifications&is_visible=true"
						field="qualifications"
						label={m.qualifications()}
						optionsLabelField="translated_name"
						baseClass="flex-1"
					/>
				</div>
				<div class="w-1/2">
					<Select
						form={_form}
						options={strengthOfKnowledgeFormChoices}
						field="strength_of_knowledge"
						label={m.strengthOfKnowledge()}
						class="flex-1"
					/>
				</div>
			</div>
			<TextArea form={_form} field="justification" label={m.justification()} />
		</div>
		<div class="flex flex-row justify-between space-x-4">
			<button
				class="btn bg-gray-400 text-white font-semibold w-full"
				data-testid="cancel-button"
				type="button"
				onclick={cancel}>{m.cancel()}</button
			>
			<button class="btn preset-filled-primary-500 font-semibold w-full" data-testid="save-button"
				>{m.save()}</button
			>
		</div>
	</SuperForm>
</div>
