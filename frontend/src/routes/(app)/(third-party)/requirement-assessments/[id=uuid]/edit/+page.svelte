<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import { RequirementAssessmentSchema } from '$lib/utils/schemas';
	import type { ActionData, PageData } from './$types';

	export let data: PageData;
	export let form: ActionData;

	const threats = data.requirementAssessment.requirement.associated_threats ?? [];
	const reference_controls =
		data.requirementAssessment.requirement.associated_reference_controls ?? [];
	const annotation = data.requirement.annotation;
	const typical_evidence = data.requirement.typical_evidence;

	const has_threats = threats.length > 0;
	const has_reference_controls = reference_controls.length > 0;

	import { page } from '$app/stores';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import HiddenInput from '$lib/components/Forms/HiddenInput.svelte';
	import Score from '$lib/components/Forms/Score.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { getOptions } from '$lib/utils/crud';
	import { getSecureRedirect } from '$lib/utils/helpers';
	import {
		ProgressRadial,
		Tab,
		TabGroup,
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '@skeletonlabs/skeleton';

	import { complianceResultColorMap } from '$lib/utils/constants';
	import { hideSuggestions } from '$lib/utils/stores';
	import * as m from '$paraglide/messages';

	import Question from '$lib/components/Forms/Question.svelte';
	import List from '$lib/components/List/List.svelte';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import { zod } from 'sveltekit-superforms/adapters';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';

	function cancel(): void {
		var currentUrl = window.location.href;
		var url = new URL(currentUrl);
		var nextValue = getSecureRedirect(url.searchParams.get('next'));
		if (nextValue) window.location.href = nextValue;
	}

	const complianceAssessmentURL = `/compliance-assessments/${data.requirementAssessment.compliance_assessment.id}`;
	const schema = RequirementAssessmentSchema;

	const modalStore: ModalStore = getModalStore();

	function modalMeasureCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.measureCreateForm,
				formAction: '?/createAppliedControl',
				model: data.measureModel,
				debug: false,
				suggestions: { reference_control: reference_controls }
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

	function modalEvidenceCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.evidenceCreateForm,
				formAction: '?/createEvidence',
				model: data.evidenceModel,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: safeTranslate('add-' + data.evidenceModel.localName)
		};
		modalStore.trigger(modal);
	}

	let createAppliedControlsLoading = false;

	function modalConfirmCreateSuggestedControls(id: string, name: string, action: string): void {
		const modalComponent: ModalComponent = {
			ref: ConfirmModal,
			props: {
				_form: data.form,
				id: id,
				debug: false,
				URLModel: 'requirement-assessments',
				formAction: action,
				bodyComponent: List,
				bodyProps: {
					items: reference_controls,
					message: m.theFollowingControlsWillBeAddedColon()
				}
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.suggestControls(),
			body: m.createAppliedControlsFromSuggestionsConfirmMessage({
				count: reference_controls.length,
				message: m.theFollowingControlsWillBeAddedColon()
			}),
			response: (r: boolean) => {
				createAppliedControlsLoading = r;
			}
		};
		modalStore.trigger(modal);
	}

	$: if (createAppliedControlsLoading === true && form) createAppliedControlsLoading = false;

	$: mappingInference = {
		sourceRequirementAssessment:
			data.requirementAssessment.mapping_inference.source_requirement_assessment,
		result: data.requirementAssessment.mapping_inference.result,
		annotation: ''
	};

	let requirementAssessmentsList: string[] = $hideSuggestions;

	let hideSuggestion = requirementAssessmentsList.includes(data.requirementAssessment.id)
		? true
		: false;

	function toggleSuggestions() {
		if (!requirementAssessmentsList.includes(data.requirementAssessment.id)) {
			requirementAssessmentsList.push(data.requirementAssessment.id);
		} else {
			requirementAssessmentsList = requirementAssessmentsList.filter(
				(item) => item !== data.requirementAssessment.id
			);
		}
		hideSuggestion = !hideSuggestion;
		hideSuggestions.set(requirementAssessmentsList);
	}

	$: classesText =
		complianceResultColorMap[mappingInference.result] === '#000000' ? 'text-white' : '';

	let tabSet = $page.data.user.is_third_party ? 1 : 0;
</script>

<div class="card space-y-2 p-4 bg-white shadow">
	<div class="flex justify-between">
		<span class="code left h-min">{data.requirement.urn}</span>
		<a class="text-pink-500 hover:text-pink-400" href={complianceAssessmentURL}
			><i class="fa-solid fa-turn-up"></i></a
		>
	</div>
	{#if data.requirement.description}
		<p class="whitespace-pre-line p-2 font-light text-lg">
			👉 {data.requirement.description}
		</p>
	{/if}
	{#if has_threats || has_reference_controls || annotation || mappingInference.result}
		<div class="card p-4 variant-glass-primary text-sm flex flex-col justify-evenly cursor-auto">
			<h2 class="font-semibold text-lg flex flex-row justify-between">
				<div>
					<i class="fa-solid fa-circle-info mr-2" />{m.additionalInformation()}
				</div>
				<button on:click={toggleSuggestions}>
					{#if !hideSuggestion}
						<i class="fa-solid fa-eye" />
					{:else}
						<i class="fa-solid fa-eye-slash" />
					{/if}
				</button>
			</h2>
			{#if !hideSuggestion}
				{#if has_threats || has_reference_controls}
					<div class="my-2 flex flex-col">
						<div class="flex-1">
							{#if reference_controls.length > 0}
								<p class="font-medium">
									<i class="fa-solid fa-gears" />
									{m.suggestedReferenceControls()}
								</p>
								<ul class="list-disc ml-4">
									{#each reference_controls as func}
										<li>
											{#if func.id}
												<a class="anchor" href="/reference-controls/{func.id}">
													{func.str}
												</a>
											{:else}
												<p>{func.str}</p>
											{/if}
										</li>
									{/each}
								</ul>
							{/if}
						</div>
						<div class="flex-1">
							{#if threats.length > 0}
								<p class="font-medium">
									<i class="fa-solid fa-gears" />
									{m.threatsCovered()}
								</p>
								<ul class="list-disc ml-4">
									{#each threats as threat}
										<li>
											{#if threat.id}
												<a class="anchor" href="/threats/{threat.id}">
													{threat.str}
												</a>
											{:else}
												<p>{threat.str}</p>
											{/if}
										</li>
									{/each}
								</ul>
							{/if}
						</div>
					</div>
				{/if}
				{#if annotation}
					<div class="my-2">
						<p class="font-medium">
							<i class="fa-solid fa-pencil" />
							{m.annotation()}
						</p>
						<p class="whitespace-pre-line py-1">
							{annotation}
						</p>
					</div>
				{/if}
				{#if typical_evidence}
					<div class="my-2">
						<p class="font-medium">
							<i class="fa-solid fa-pencil" />
							{m.typicalEvidence()}
						</p>
						<p class="whitespace-pre-line py-1">
							{typical_evidence}
						</p>
					</div>
				{/if}
				{#if mappingInference.result}
					<div class="my-2">
						<p class="font-medium">
							<i class="fa-solid fa-link" />
							{m.mappingInference()}
						</p>
						<span class="text-xs text-gray-500"
							><i class="fa-solid fa-circle-info"></i> {m.mappingInferenceHelpText()}</span
						>
						<ul class="list-disc ml-4">
							<li>
								<p>
									<a
										class="anchor"
										href="/requirement-assessments/{mappingInference.sourceRequirementAssessment
											.id}"
									>
										{mappingInference.sourceRequirementAssessment.str}
									</a>
								</p>
								<p class="whitespace-pre-line py-1">
									<span class="italic">{m.coverageColon()}</span>
									<span class="badge h-fit">
										{safeTranslate(mappingInference.sourceRequirementAssessment.coverage)}
									</span>
								</p>
								{#if mappingInference.sourceRequirementAssessment.is_scored}
									<p class="whitespace-pre-line py-1">
										<span class="italic">{m.scoreSemiColon()}</span>
										<span class="badge h-fit">
											{safeTranslate(mappingInference.sourceRequirementAssessment.score)}
										</span>
									</p>
								{/if}
								<p class="whitespace-pre-line py-1">
									<span class="italic">{m.suggestionColon()}</span>
									<span
										class="badge {classesText} h-fit"
										style="background-color: {complianceResultColorMap[mappingInference.result]};"
									>
										{safeTranslate(mappingInference.result)}
									</span>
								</p>
								{#if mappingInference.annotation}
									<p class="whitespace-pre-line py-1">
										<span class="italic">{m.annotationColon()}</span>
										{mappingInference.annotation}
									</p>
								{/if}
							</li>
						</ul>
					</div>
				{/if}
			{/if}
		</div>
	{/if}
	<div class="mt-4">
		<SuperForm
			class="flex flex-col"
			data={data.form}
			dataType="json"
			let:form
			let:data
			validators={zod(schema)}
			action="?/updateRequirementAssessment"
			{...$$restProps}
		>
			<div class="card shadow-lg bg-white">
				<TabGroup>
					{#if !$page.data.user.is_third_party}
						<Tab bind:group={tabSet} name="compliance_assessments_tab" value={0}
							>{m.appliedControls()}
						</Tab>
					{/if}
					<Tab bind:group={tabSet} name="risk_assessments_tab" value={1}>{m.evidences()}</Tab>
					<svelte:fragment slot="panel">
						{#if tabSet === 0 && !$page.data.user.is_third_party}
							<div class="flex items-center mb-2 px-2 text-xs space-x-2">
								<i class="fa-solid fa-info-circle" />
								<p>{m.requirementAppliedControlHelpText()}</p>
							</div>
							<div
								class="h-full flex flex-col space-y-2 variant-outline-surface rounded-container-token p-4"
							>
								<span class="flex flex-row justify-end items-center space-x-2">
									{#if Object.hasOwn($page.data.user.permissions, 'add_appliedcontrol') && reference_controls.length > 0}
										<button
											class="btn text-gray-100 bg-gradient-to-r from-fuchsia-500 to-pink-500 h-fit whitespace-normal"
											type="button"
											on:click={() => {
												modalConfirmCreateSuggestedControls(
													$page.data.requirementAssessment.id,
													$page.data.requirementAssessment.name,
													'?/createSuggestedControls'
												);
											}}
										>
											<span class="mr-2">
												{#if createAppliedControlsLoading}
													<ProgressRadial
														class="-ml-2"
														width="w-6"
														meter="stroke-white"
														stroke={80}
													/>
												{:else}
													<i class="fa-solid fa-fire-extinguisher" />
												{/if}
											</span>
											{m.suggestControls()}
										</button>
									{/if}
									<button
										class="btn variant-filled-primary self-end"
										on:click={modalMeasureCreateForm}
										type="button"><i class="fa-solid fa-plus mr-2" />{m.addAppliedControl()}</button
									>
								</span>
								<AutocompleteSelect
									multiple
									{form}
									options={getOptions({
										objects: $page.data.model.foreignKeys['applied_controls'],
										extra_fields: [['folder', 'str']]
									})}
									field="applied_controls"
								/>
								<ModelTable
									source={$page.data.tables['applied-controls']}
									hideFilters={true}
									URLModel="applied-controls"
								/>
							</div>
						{/if}
						{#if tabSet === 1}
							<div class="flex items-center mb-2 px-2 text-xs space-x-2">
								<i class="fa-solid fa-info-circle" />
								<p>{m.requirementEvidenceHelpText()}</p>
							</div>
							<div
								class="h-full flex flex-col space-y-2 variant-outline-surface rounded-container-token p-4"
							>
								<span class="flex flex-row justify-end items-center">
									<button
										class="btn variant-filled-primary self-end"
										on:click={modalEvidenceCreateForm}
										type="button"><i class="fa-solid fa-plus mr-2" />{m.addEvidence()}</button
									>
								</span>
								<AutocompleteSelect
									multiple
									{form}
									options={getOptions({
										objects: $page.data.model.foreignKeys['evidences'],
										extra_fields: [['folder', 'str']]
									})}
									field="evidences"
								/>
								<ModelTable
									source={$page.data.tables['evidences']}
									hideFilters={true}
									URLModel="evidences"
								/>
							</div>
						{/if}
					</svelte:fragment>
				</TabGroup>
			</div>
			<HiddenInput {form} field="folder" />
			<HiddenInput {form} field="requirement" />
			<HiddenInput {form} field="compliance_assessment" />
			<div class="flex flex-col my-8 space-y-6">
				{#if $page.data.requirementAssessment.answer != null && Object.keys($page.data.requirementAssessment.answer).length !== 0}
					<Question {form} field="answer" label={m.question()} />
				{/if}
				<Select
					{form}
					options={$page.data.model.selectOptions['status']}
					field="status"
					label={m.status()}
				/>
				<Select
					{form}
					options={$page.data.model.selectOptions['result']}
					field="result"
					label={m.result()}
				/>
				<div class="flex flex-col">
					<Score
						{form}
						min_score={$page.data.compliance_assessment_score.min_score}
						max_score={$page.data.compliance_assessment_score.max_score}
						scores_definition={$page.data.compliance_assessment_score.scores_definition}
						field="score"
						label={$page.data.compliance_assessment_score.show_documentation_score
							? m.implementationScore()
							: m.score()}
						disabled={!data.is_scored || data.result === 'not_applicable'}
					>
						<div slot="left">
							<Checkbox
								{form}
								field="is_scored"
								label={''}
								helpText={m.scoringHelpText()}
								checkboxComponent="switch"
								class="h-full flex flex-row items-center justify-center my-1"
								classesContainer="h-full flex flex-row items-center space-x-4"
							/>
						</div>
					</Score>
				</div>
				{#if $page.data.compliance_assessment_score.show_documentation_score}
					<Score
						{form}
						min_score={$page.data.compliance_assessment_score.min_score}
						max_score={$page.data.compliance_assessment_score.max_score}
						scores_definition={$page.data.compliance_assessment_score.scores_definition}
						field="documentation_score"
						label={m.documentationScore()}
						isDoc={true}
						disabled={!data.is_scored || data.result === 'not_applicable'}
					/>
				{/if}

				<TextArea {form} field="observation" label="Observation" />
				<div class="flex flex-row justify-between space-x-4">
					<button
						class="btn bg-gray-400 text-white font-semibold w-full"
						type="button"
						on:click={cancel}>{m.cancel()}</button
					>
					<button
						class="btn variant-filled-primary font-semibold w-full"
						data-testid="save-button"
						type="submit">{m.save()}</button
					>
				</div>
			</div>
		</SuperForm>
	</div>
</div>
