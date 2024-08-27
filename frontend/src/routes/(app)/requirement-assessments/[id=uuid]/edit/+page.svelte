<script lang="ts">
	import { RequirementAssessmentSchema } from '$lib/utils/schemas';
	import type { PageData } from '../[id=uuid]/edit/$types';

	export let data: PageData;
	const threats = data.requirement.threats;
	const reference_controls = data.requirement.reference_controls;
	const annotation = data.requirement.annotation;

	const has_threats = threats && threats.length > 0;
	const has_reference_controls = reference_controls && reference_controls.length > 0;

	import { page } from '$app/stores';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import HiddenInput from '$lib/components/Forms/HiddenInput.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import Score from '$lib/components/Forms/Score.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { getOptions } from '$lib/utils/crud';
	import { getSecureRedirect } from '$lib/utils/helpers';
	import { breadcrumbObject } from '$lib/utils/stores';
	import {
		getModalStore,
		getToastStore,
		Tab,
		type ModalComponent,
		type ModalSettings,
		type ModalStore,
		type ToastStore,
		TabGroup
	} from '@skeletonlabs/skeleton';
	import { superForm } from 'sveltekit-superforms';

	import { localItems, capitalizeFirstLetter, toCamelCase } from '$lib/utils/locales';
	import { complianceResultColorMap } from '$lib/utils/constants';
	import * as m from '$paraglide/messages';
	import { hideSuggestions } from '$lib/utils/stores';

	import { getRequirementTitle } from '$lib/utils/helpers';
	import { zod } from 'sveltekit-superforms/adapters';
	import Question from '$lib/components/Forms/Question.svelte';

	function cancel(): void {
		var currentUrl = window.location.href;
		var url = new URL(currentUrl);
		var nextValue = getSecureRedirect(url.searchParams.get('next'));
		if (nextValue) window.location.href = nextValue;
	}

	const title = getRequirementTitle(data.requirement.ref_id, data.requirement.name)
		? getRequirementTitle(data.requirement.ref_id, data.requirement.name)
		: getRequirementTitle(data.parent.ref_id, data.parent.name);
	breadcrumbObject.set({
		id: data.requirementAssessment.id,
		name: title ?? 'Requirement assessment',
		email: ''
	});

	const schema = RequirementAssessmentSchema;

	const modalStore: ModalStore = getModalStore();
	const toastStore: ToastStore = getToastStore();

	function modalMeasureCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.measureCreateForm,
				formAction: 'createAppliedControl',
				model: data.measureModel,
				debug: false,
				suggestions: { reference_control: reference_controls }
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

	function modalEvidenceCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.evidenceCreateForm,
				formAction: 'createEvidence',
				model: data.evidenceModel,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: localItems()['add' + capitalizeFirstLetter(data.evidenceModel.localName)]
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
	let { form: evidenceCreateForm, message: evidenceCreateMessage } = {
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
		({ form: evidenceCreateForm, message: evidenceCreateMessage } = superForm(
			data.evidenceCreateForm,
			{
				onUpdated: ({ form }) =>
					handleFormUpdated({ form, pageStatus: $page.status, closeModal: true })
			}
		));
	}

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

	let tabSet = 0;
</script>

<div class="card space-y-2 p-4 bg-white shadow">
	<code class="code">{data.requirement.urn}</code>
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
				{#if mappingInference.result}
					<div class="my-2">
						<p class="font-medium">
							<i class="fa-solid fa-link" />
							{m.mappingInference()}
						</p>
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
									<span class="badge {classesText} h-fit">
										{m[mappingInference.sourceRequirementAssessment.coverage]()}
									</span>
								</p>
								<p class="whitespace-pre-line py-1">
									<span class="italic">{m.suggestionColon()}</span>
									<span
										class="badge {classesText} h-fit"
										style="background-color: {complianceResultColorMap[mappingInference.result]};"
									>
										{m[toCamelCase(mappingInference.result)]()}
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
			validators={zod(schema)}
			action="?/updateRequirementAssessment"
			{...$$restProps}
		>
			<div class="card shadow-lg bg-white">
				<TabGroup>
					<Tab bind:group={tabSet} name="compliance_assessments_tab" value={0}
						>{m.appliedControls()}
					</Tab>
					<Tab bind:group={tabSet} name="risk_assessments_tab" value={1}>{m.evidences()}</Tab>
					<svelte:fragment slot="panel">
						{#if tabSet === 0}
							<div class="flex items-center mb-2 px-2 text-xs space-x-2">
								<i class="fa-solid fa-info-circle" />
								<p>{m.requirementAppliedControlHelpText()}</p>
							</div>
							<div
								class="h-full flex flex-col space-y-2 variant-outline-surface rounded-container-token p-4"
							>
								<span class="flex flex-row justify-end items-center">
									<button
										class="btn variant-filled-primary self-end"
										on:click={modalMeasureCreateForm}
										type="button"><i class="fa-solid fa-plus mr-2" />{m.addAppliedControl()}</button
									>
								</span>
								<AutocompleteSelect
									multiple
									{form}
									options={getOptions({ objects: data.model.foreignKeys['applied_controls'] })}
									field="applied_controls"
								/>
								<ModelTable
									source={data.tables['applied-controls']}
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
									options={getOptions({ objects: data.model.foreignKeys['evidences'] })}
									field="evidences"
								/>
								<ModelTable
									source={data.tables['evidences']}
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
				{#if Object.keys(data.requirementAssessment.answer).length !== 0}
					<Question {form} field="answer" label={m.question()} />
				{/if}
				<Select
					{form}
					options={data.model.selectOptions['status']}
					field="status"
					label={m.status()}
				/>
				<Select
					{form}
					options={data.model.selectOptions['result']}
					field="result"
					label={m.result()}
				/>
				<Score
					{form}
					min_score={data.compliance_assessment_score.min_score}
					max_score={data.compliance_assessment_score.max_score}
					scores_definition={data.compliance_assessment_score.scores_definition}
					field="score"
					label="Score"
				/>

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
