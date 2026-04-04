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
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';

	import { browser } from '$app/environment';
	import { page } from '$app/state';

	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
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
		class="flex flex-col space-y-4"
		data={data.form}
		dataType="json"
		{_form}
		validators={zod(schema)}
		action="?/updateRiskScenario&next={next}"
	>
		<!-- ── Context Bar ── -->
		<div class="flex flex-col sm:flex-row gap-3">
			<div class="card px-5 py-3 bg-white shadow-lg flex-1">
				<div class="flex items-center gap-2 mb-2">
					<i class="fa-solid fa-layer-group text-xs text-indigo-400"></i>
					<span class="text-xs font-semibold uppercase tracking-wider text-gray-400"
						>{m.scope()}</span
					>
				</div>
				<div class="flex flex-wrap gap-x-6 gap-y-1">
					{#if data.scenario.risk_assessment.perimeter}
						<div>
							<p class="text-xs text-gray-400">{m.perimeter()}</p>
							<Anchor
								class="anchor text-sm font-semibold"
								href="/perimeters/{data.scenario.perimeter.id}"
								>{data.scenario.perimeter.str}</Anchor
							>
						</div>
					{/if}
					<div>
						<p class="text-xs text-gray-400">{m.riskAssessment()}</p>
						<Anchor
							class="anchor text-sm font-semibold"
							href="/risk-assessments/{data.scenario.risk_assessment.id}"
							>{data.scenario.risk_assessment.name} {data.scenario.version}</Anchor
						>
					</div>
					<div>
						<p class="text-xs text-gray-400">{m.riskMatrix()}</p>
						<Anchor
							class="anchor text-sm font-semibold"
							href="/risk-matrices/{data.scenario.risk_matrix.id}"
							target="_blank"
							rel="noopener noreferrer">{data.scenario.risk_matrix.str}</Anchor
						>
					</div>
				</div>
			</div>
			<div class="card px-5 py-3 bg-white shadow-lg flex-1">
				<div class="flex items-center gap-2 mb-2">
					<i class="fa-solid fa-user-gear text-xs text-indigo-400"></i>
					<span class="text-xs font-semibold uppercase tracking-wider text-gray-400"
						>{m.ownership()}</span
					>
				</div>
				<div class="flex flex-row items-stretch gap-4">
					<div class="flex-1">
						<AutocompleteSelect
							form={_form}
							multiple
							optionsEndpoint="actors"
							optionsLabelField="str"
							optionsInfoFields={{
								fields: [{ field: 'type', translate: true }],
								position: 'prefix'
							}}
							field="owner"
							label={m.owner()}
						/>
					</div>
					<div class="w-48">
						<Select
							form={_form}
							options={data.treatmentChoices}
							field="treatment"
							label={m.treatmentStatus()}
						/>
					</div>
				</div>
			</div>
		</div>

		<!-- ── Identity & Relations ── -->
		<div class="flex flex-col lg:flex-row gap-3">
			<div class="card px-5 py-4 bg-white shadow-lg lg:w-5/12 space-y-3">
				<div class="flex items-center gap-2 mb-1">
					<i class="fa-solid fa-fingerprint text-xs text-indigo-400"></i>
					<span class="text-xs font-semibold uppercase tracking-wider text-gray-400"
						>{m.identification()}</span
					>
				</div>
				<div class="flex gap-3">
					<div class="w-28 shrink-0">
						<TextField form={_form} field="ref_id" label={m.refId()} />
					</div>
					<div class="flex-1">
						<TextField form={_form} field="name" label={m.name()} classesContainer="w-full" />
					</div>
				</div>
				<MarkdownField form={_form} field="description" rows={6} label={m.description()} />
			</div>
			<div class="card px-5 py-4 bg-white shadow-lg lg:w-7/12 max-h-[26rem] overflow-y-auto">
				<div class="flex items-center gap-2 mb-3">
					<i class="fa-solid fa-diagram-project text-xs text-indigo-400"></i>
					<span class="text-xs font-semibold uppercase tracking-wider text-gray-400"
						>{m.associatedObjects()}</span
					>
				</div>
				<div class="space-y-2">
					<AutocompleteSelect
						multiple
						form={_form}
						optionsEndpoint="assets"
						lazy
						optionsLabelField="auto"
						optionsExtraFields={[['folder', 'str']]}
						optionsInfoFields={{
							fields: [{ field: 'type' }],
							classes: 'text-blue-500'
						}}
						field="assets"
						optionsDetailedUrlParameters={[['scope_folder_id', page.data.scenario.folder.id]]}
						label={m.assets()}
					/>
					<AutocompleteSelect
						form={_form}
						multiple
						optionsEndpoint="threats"
						optionsDetailedUrlParameters={[['scope_folder_id', page.data.scenario.folder.id]]}
						optionsExtraFields={[['folder', 'str']]}
						optionsLabelField="auto"
						field="threats"
						label={m.threats()}
					/>
					<AutocompleteSelect
						multiple
						form={_form}
						optionsEndpoint="vulnerabilities"
						optionsDetailedUrlParameters={[['scope_folder_id', page.data.scenario.folder.id]]}
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
		</div>

		<!-- ── Risk Origin & Antecedent Scenarios ── -->
		<div class="flex flex-col sm:flex-row gap-3">
			<div class="card px-5 py-4 bg-white shadow-lg flex-1">
				<div class="flex items-center gap-2 mb-2">
					<i class="fa-solid fa-crosshairs text-xs text-indigo-400"></i>
					<span class="text-xs font-semibold uppercase tracking-wider text-gray-400"
						>{m.riskOrigin()}</span
					>
				</div>
				<AutocompleteSelect
					form={_form}
					nullable
					optionsEndpoint="terminologies?field_path=ro_to.risk_origin&is_visible=true"
					optionsLabelField="translated_name"
					field="risk_origin"
					label={m.riskOrigin()}
					helpText={m.riskOriginHelpText()}
				/>
			</div>
			<div class="card px-5 py-4 bg-white shadow-lg flex-1">
				<div class="flex items-center gap-2 mb-2">
					<i class="fa-solid fa-timeline text-xs text-indigo-400"></i>
					<span class="text-xs font-semibold uppercase tracking-wider text-gray-400"
						>{m.antecedentScenarios()}</span
					>
				</div>
				<AutocompleteSelect
					form={_form}
					multiple
					optionsEndpoint="risk-scenarios"
					optionsExtraFields={[
						['risk_assessment', 'str'],
						['ref_id', 'str']
					]}
					optionsDetailedUrlParameters={[['exclude', data.scenario.id]]}
					optionsLabelField="auto"
					field="antecedent_scenarios"
					label={m.antecedentScenarios()}
					helpText={m.antecedentScenariosHelpText()}
				/>
			</div>
		</div>

		<input type="hidden" name="urlmodel" value={data.model.urlModel} />

		<!-- ── Risk Assessment Flow ── -->
		<div class="space-y-0">
			{#if page.data?.featureflags?.inherent_risk}
				<!-- Inherent Risk -->
				<div
					class="card px-5 pt-4 pb-14 bg-white shadow-lg border-l-4 border-l-orange-400 rounded-b-none"
				>
					<div class="flex items-center gap-2 mb-3">
						<i class="fa-solid fa-fire text-sm text-orange-400"></i>
						<h4 class="text-base font-bold text-gray-800">{m.inherentRisk()}</h4>
						<span class="text-xs text-gray-400 ml-1">{m.riskOptionHelper()}</span>
					</div>
					<div class="flex items-center gap-4 flex-wrap">
						<div class="min-w-36">
							<Select
								form={_form}
								options={data.probabilityChoices}
								color_map={probabilityColorMap}
								field="inherent_proba"
								label={m.inherentProba()}
							/>
						</div>
						<span
							class="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-400 text-xs font-bold select-none mt-5"
							>&times;</span
						>
						<div class="min-w-36">
							<Select
								form={_form}
								options={data.impactChoices}
								color_map={impactColorMap}
								field="inherent_impact"
								label={m.inherentImpact()}
							/>
						</div>
						<span
							class="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-400 text-xs font-bold select-none mt-5"
							>=</span
						>
						<div>
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
				<!-- Flow connector -->
				<div class="flex items-center pl-6 -my-px">
					<div class="w-0.5 h-5 bg-gray-300"></div>
					<i class="fa-solid fa-chevron-down text-[10px] text-gray-300 -ml-[5px] mt-3"></i>
				</div>
			{/if}

			<!-- Current Risk -->
			<div
				class="card px-5 pt-4 pb-14 bg-white shadow-lg border-l-4 border-l-amber-400 {page.data
					?.featureflags?.inherent_risk
					? 'rounded-none'
					: 'rounded-b-none'}"
			>
				<div class="flex items-center gap-2 mb-3">
					<i class="fa-solid fa-gauge-high text-sm text-amber-500"></i>
					<h4 class="text-base font-bold text-gray-800">{m.currentRisk()}</h4>
				</div>
				<div class="flex flex-col xl:flex-row xl:items-center gap-6">
					<!-- Existing controls -->
					<div class="xl:w-1/2">
						<div class="flex items-center gap-2">
							<div class="flex-1">
								{#key refreshKey}
									<AutocompleteSelect
										multiple
										form={_form}
										optionsEndpoint="applied-controls"
										optionsExtraFields={[['folder', 'str']]}
										optionsDetailedUrlParameters={[
											['scope_folder_id', page.data.scenario.folder.id]
										]}
										field="existing_applied_controls"
										label={m.existingControls()}
										helpText={m.existingControlsHelper()}
									/>
								{/key}
							</div>
							<button
								class="btn preset-tonal-primary shrink-0 h-10 w-10"
								onclick={(_) => modalMeasureCreateForm('existing_applied_controls')}
								type="button"
							>
								<i class="fa-solid fa-plus text-sm"></i>
							</button>
						</div>
					</div>
					<!-- Risk equation -->
					<div class="xl:w-1/2">
						<div class="flex items-center gap-4 flex-wrap">
							<div class="min-w-36">
								<Select
									form={_form}
									options={data.probabilityChoices}
									color_map={probabilityColorMap}
									field="current_proba"
									label={m.currentProba()}
								/>
							</div>
							<span
								class="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-400 text-xs font-bold select-none mt-5"
								>&times;</span
							>
							<div class="min-w-36">
								<Select
									form={_form}
									options={data.impactChoices}
									color_map={impactColorMap}
									field="current_impact"
									label={m.currentImpact()}
								/>
							</div>
							<span
								class="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-400 text-xs font-bold select-none mt-5"
								>=</span
							>
							<div>
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

			<!-- Flow connector -->
			<div class="flex items-center pl-6 -my-px">
				<div class="w-0.5 h-5 bg-gray-300"></div>
				<i class="fa-solid fa-chevron-down text-[10px] text-gray-300 -ml-[5px] mt-3"></i>
			</div>

			<!-- Residual Risk -->
			<div
				class="card px-5 pt-4 pb-14 bg-white shadow-lg border-l-4 border-l-emerald-400 rounded-t-none"
			>
				<div class="flex items-center gap-2 mb-3">
					<i class="fa-solid fa-shield-halved text-sm text-emerald-500"></i>
					<h4 class="text-base font-bold text-gray-800">{m.residualRisk()}</h4>
				</div>
				<div class="flex flex-col xl:flex-row xl:items-center gap-6">
					<!-- Extra controls -->
					<div class="xl:w-1/2">
						<div class="flex items-center gap-2">
							<div class="flex-1">
								{#key refreshKey}
									<AutocompleteSelect
										multiple
										form={_form}
										optionsEndpoint="applied-controls"
										optionsExtraFields={[['folder', 'str']]}
										optionsDetailedUrlParameters={[
											['scope_folder_id', page.data.scenario.folder.id]
										]}
										field="applied_controls"
										label={m.extraAppliedControls()}
										helpText={m.extraControlsHelper()}
									/>
								{/key}
							</div>
							<button
								class="btn preset-tonal-primary shrink-0 h-10 w-10"
								onclick={(_) => modalMeasureCreateForm('applied_controls')}
								type="button"
							>
								<i class="fa-solid fa-plus text-sm"></i>
							</button>
						</div>
					</div>
					<!-- Risk equation -->
					<div class="xl:w-1/2">
						<div class="flex items-center gap-4 flex-wrap">
							<div class="min-w-36">
								<Select
									form={_form}
									options={data.probabilityChoices}
									color_map={probabilityColorMap}
									field="residual_proba"
									label={m.residualProba()}
								/>
							</div>
							<span
								class="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-400 text-xs font-bold select-none mt-5"
								>&times;</span
							>
							<div class="min-w-36">
								<Select
									form={_form}
									options={data.impactChoices}
									color_map={impactColorMap}
									field="residual_impact"
									label={m.residualImpact()}
								/>
							</div>
							<span
								class="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-400 text-xs font-bold select-none mt-5"
								>=</span
							>
							<div>
								<RiskLevel
									form={_form}
									field="residual_risk_level"
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
		</div>

		<!-- ── Assessment Details ── -->
		<div class="card px-5 py-4 bg-white shadow-lg">
			<div class="flex items-center gap-2 mb-3">
				<i class="fa-solid fa-clipboard-check text-xs text-indigo-400"></i>
				<span class="text-xs font-semibold uppercase tracking-wider text-gray-400"
					>{m.assessmentDetails()}</span
				>
			</div>
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
				<AutocompleteSelect
					form={_form}
					multiple
					optionsEndpoint="terminologies?field_path=qualifications&is_visible=true"
					field="qualifications"
					label={m.qualifications()}
					optionsLabelField="translated_name"
				/>
				<Select
					form={_form}
					options={strengthOfKnowledgeFormChoices}
					field="strength_of_knowledge"
					label={m.strengthOfKnowledge()}
				/>
			</div>
			<div class="mt-3">
				<MarkdownField form={_form} field="justification" label={m.justification()} />
			</div>
			<div class="mt-3">
				<AutocompleteSelect
					multiple
					form={_form}
					createFromSelection={true}
					optionsEndpoint="filtering-labels"
					optionsLabelField="label"
					field="filtering_labels"
					helpText={m.labelsHelpText()}
					label={m.labels()}
					translateOptions={false}
					allowUserOptions="append"
				/>
			</div>
		</div>

		<!-- ── Sticky Footer ── -->
		<div
			class="flex flex-row justify-between gap-4 sticky bottom-0 bg-white/80 backdrop-blur-md pt-3 pb-3 px-1 -mx-1 border-t border-gray-200 z-10"
		>
			<button
				class="btn preset-tonal-surface font-semibold w-full"
				data-testid="cancel-button"
				type="button"
				onclick={cancel}
			>
				<i class="fa-solid fa-xmark mr-1.5 text-sm"></i>
				{m.cancel()}
			</button>
			<button class="btn preset-filled-primary-500 font-semibold w-full" data-testid="save-button">
				<i class="fa-solid fa-check mr-1.5 text-sm"></i>
				{m.save()}
			</button>
		</div>
	</SuperForm>
</div>
