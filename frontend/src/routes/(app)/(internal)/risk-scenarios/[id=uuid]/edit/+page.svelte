<script lang="ts">
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { getOptions } from '$lib/utils/crud';
	import { getSecureRedirect } from '$lib/utils/helpers';
	import { modelSchema } from '$lib/utils/schemas';
	import type { StrengthOfKnowledgeEntry } from '$lib/utils/types';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '@skeletonlabs/skeleton';
	import type { PageData } from './$types';
	import RiskLevel from './RiskLevel.svelte';

	import { browser } from '$app/environment';
	import { page } from '$app/stores';

	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import * as m from '$paraglide/messages';
	import { zod } from 'sveltekit-superforms/adapters';

	export let data: PageData;

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

	function modalMeasureCreateForm(field: string): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.measureCreateForm,
				formAction: '?/createAppliedControl&field=' + field,
				model: data.measureModel,
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

	const next = getSecureRedirect($page.url.searchParams.get('next'));

	const probabilityColorMap = data.riskMatrix.probability.map(
		(probability) => probability.hexcolor
	);
	const impactColorMap = data.riskMatrix.impact.map((impact) => impact.hexcolor);
</script>

{#key data.scenario}
	<div>
		<SuperForm
			class="flex flex-col space-y-3"
			data={data.form}
			dataType="json"
			let:form
			validators={zod(schema)}
			action="?/updateRiskScenario&next={next}"
			{...$$restProps}
		>
			<div class="flex flex-row space-x-2">
				<div class="card p-2 bg-white shadow-lg w-1/2">
					<div class="flex justify-between p-2">
						<div>
							<p class="text-sm font-semibold text-gray-400">{m.project()}</p>
							<Anchor
								class="anchor text-sm font-semibold"
								href="/projects/{data.scenario.project.id}">{data.scenario.project.str}</Anchor
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
					</div>
				</div>
				<div class="card px-4 py-2 bg-white shadow-lg w-1/2">
					<div class="flex flex-row justify-between">
						<div class=" px-2 w-2/3">
							<AutocompleteSelect
								{form}
								multiple
								options={getOptions({ objects: data.foreignKeys['owner'], label: 'email' })}
								field="owner"
								label={m.owner()}
							/>
						</div>
						<div class="w-1/3">
							<Select
								class="h-14"
								{form}
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
						<TextField {form} field="ref_id" label={m.refId()} />
						<TextField {form} field="name" label={m.name()} classesContainer="w-full" />
					</span>
					<TextArea {form} field="description" rows={6} label={m.description()} />
				</div>
				<div class="card px-4 py-2 bg-white shadow-lg w-7/12 max-h-96 overflow-y-scroll">
					<AutocompleteSelect
						multiple
						{form}
						options={getOptions({
							objects: data.foreignKeys['assets'],
							extra_fields: [['folder', 'str']],
							label: 'auto'
						})}
						field="assets"
						label={m.assets()}
						helpText={m.riskScenarioAssetHelpText()}
					/>
					<AutocompleteSelect
						{form}
						multiple
						options={getOptions({
							objects: data.foreignKeys['threats'],
							extra_fields: [['folder', 'str']],
							label: 'auto'
						})}
						field="threats"
						label={m.threats()}
					/>
					<AutocompleteSelect
						multiple
						{form}
						options={getOptions({
							objects: data.foreignKeys['vulnerabilities'],
							extra_fields: [['folder', 'str']],
							label: 'auto'
						})}
						field="vulnerabilities"
						label={m.vulnerabilities()}
					/>
				</div>
			</div>
			<input type="hidden" name="urlmodel" value={data.model.urlModel} />

			<div class="card px-4 py-2 bg-white shadow-lg">
				<h4 class="h4 font-black mb-2">{m.currentRisk()}</h4>
				<div class="flex flex-row space-x-8 justify-between">
					<div class="w-1/2">
						<div class="flex mb-2">
							<div class="w-full mr-2">
								<AutocompleteSelect
									multiple
									{form}
									options={getOptions({
										objects: data.foreignKeys['applied_controls'],
										extra_fields: [['folder', 'str']]
									})}
									field="existing_applied_controls"
									label={m.existingControls()}
									helpText={m.existingControlsHelper()}
								/>
							</div>
							<div class="flex items-center justify-center">
								<div class="">
									<button
										class="btn bg-gray-300 h-10 w-10"
										on:click={(_) => modalMeasureCreateForm('existing_applied_controls')}
										type="button"><i class="fa-solid fa-plus text-sm" /></button
									>
								</div>
							</div>
						</div>
						<TextArea
							{form}
							field="existing_controls"
							label="context"
							helpText={m.existingContextHelper()}
							regionContainer="w-1/2"
							rows={3}
						/>
					</div>
					<div class="flex w-1/2">
						<div class="flex flex-row space-x-4 my-auto">
							<div class="min-w-36">
								<Select
									{form}
									options={data.probabilityChoices}
									color_map={probabilityColorMap}
									field="current_proba"
									label={m.currentProba()}
								/>
							</div>
							<i class="fa-solid fa-xmark mt-8" />
							<div class="min-w-36">
								<Select
									{form}
									options={data.impactChoices}
									color_map={impactColorMap}
									field="current_impact"
									label={m.currentImpact()}
								/>
							</div>
							<i class="fa-solid fa-equals mt-8" />
							<div class="min-w-38">
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
			</div>

			<div class="card px-4 py-2 bg-white shadow-lg">
				<h4 class="h4 font-black mb-2">{m.residualRisk()}</h4>
				<div class="flex flex-row space-x-8">
					<div class="w-1/2">
						<div class="flex">
							<div class="w-full mr-2">
								<AutocompleteSelect
									multiple
									{form}
									options={getOptions({
										objects: data.foreignKeys['applied_controls'],
										extra_fields: [['folder', 'str']]
									})}
									field="applied_controls"
									label={m.extraAppliedControls()}
									helpText={m.extraControlsHelper()}
								/>
							</div>
							<div class="flex items-center justify-center">
								<div class="">
									<button
										class="btn bg-gray-300 h-10 w-10"
										on:click={(_) => modalMeasureCreateForm('applied_controls')}
										type="button"><i class="fa-solid fa-plus text-sm" /></button
									>
								</div>
							</div>
						</div>
					</div>
					<div class="flex w-1/2">
						<div class="flex flex-row space-x-4 my-auto">
							<div class="min-w-36">
								<Select
									{form}
									options={data.probabilityChoices}
									color_map={probabilityColorMap}
									field="residual_proba"
									label={m.residualProba()}
								/>
							</div>
							<i class="fa-solid fa-xmark mt-8" />
							<div class="min-w-36">
								<Select
									{form}
									options={data.impactChoices}
									color_map={impactColorMap}
									field="residual_impact"
									label={m.residualImpact()}
								/>
							</div>
							<i class="fa-solid fa-equals mt-8" />
							<div class="min-w-38">
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
			</div>

			<div class="card px-4 py-2 bg-white shadow-lg">
				<div class="flex space-x-4 mb-1">
					<div class="w-1/2">
						<AutocompleteSelect
							{form}
							options={data.qualificationChoices}
							multiple={true}
							field="qualifications"
							label={m.qualification()}
						/>
					</div>
					<div class="w-1/2">
						<Select
							{form}
							options={strengthOfKnowledgeFormChoices}
							field="strength_of_knowledge"
							label={m.strengthOfKnowledge()}
							class="h-14"
						/>
					</div>
				</div>
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
{/key}
