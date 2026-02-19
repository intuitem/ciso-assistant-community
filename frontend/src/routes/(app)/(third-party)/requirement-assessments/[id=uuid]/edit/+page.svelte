<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import { RequirementAssessmentSchema } from '$lib/utils/schemas';
	import type { ActionData, PageData } from './$types';

	import { page } from '$app/state';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import HiddenInput from '$lib/components/Forms/HiddenInput.svelte';
	import Score from '$lib/components/Forms/Score.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { getSecureRedirect } from '$lib/utils/helpers';
	import { Progress, Tabs } from '@skeletonlabs/skeleton-svelte';

	import { complianceResultColorMap } from '$lib/utils/constants';
	import { hideSuggestions } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import { countMasked } from '$lib/utils/related-visibility';

	import Question from '$lib/components/Forms/Question.svelte';
	import List from '$lib/components/List/List.svelte';
	import ConfirmModal from '$lib/components/Modals/ConfirmModal.svelte';
	import { zod } from 'sveltekit-superforms/adapters';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import { superForm } from 'sveltekit-superforms';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import {
		computeRequirementScoreAndResult,
		formatScoreValue,
		displayScoreColor
	} from '$lib/utils/helpers';

	interface Props {
		data: PageData;
		form: ActionData;
		[key: string]: any;
	}

	let { data, form, ...rest }: Props = $props();

	const threats = data.requirementAssessment.requirement.associated_threats ?? [];
	const reference_controls =
		data.requirementAssessment.requirement.associated_reference_controls ?? [];
	const annotation = data.requirement.annotation;
	const typical_evidence = data.requirement.typical_evidence;

	const has_threats = threats.length > 0;
	const has_reference_controls = reference_controls.length > 0;

	// Map implementation group ref_ids to their display names
	const implementationGroupsDefinition =
		data.requirementAssessment.compliance_assessment.framework?.implementation_groups_definition ??
		[];

	function getImplementationGroupName(refId: string): string {
		return implementationGroupsDefinition.find((g) => g.ref_id === refId)?.name ?? refId;
	}

	function cancel(): void {
		var currentUrl = window.location.href;
		var url = new URL(currentUrl);
		var nextValue = getSecureRedirect(url.searchParams.get('next'));
		window.location.href = nextValue || complianceAssessmentURL;
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
				invalidateAll: false,
				origin: 'requirement-assessments',
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
				invalidateAll: false,
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

	function modalSecurityExceptionCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.securityExceptionCreateForm,
				formAction: '?/createSecurityException',
				model: data.securityExceptionModel,
				invalidateAll: false,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: safeTranslate('add-' + data.securityExceptionModel.localName)
		};
		modalStore.trigger(modal);
	}

	let createAppliedControlsLoading = $state(false);

	async function modalConfirmCreateSuggestedControls(id: string, name: string, action: string) {
		let previewItems: string[] = [];
		try {
			const previewResponse = await fetch(
				`/requirement-assessments/${id}/suggestions/applied-controls?dry_run=true`
			);
			if (previewResponse.ok) {
				const previewData: any[] = await previewResponse.json();
				previewItems = previewData.map(
					(control) =>
						control?.name ||
						control?.reference_control?.str ||
						control?.reference_control?.name ||
						control?.ref_id ||
						''
				);
			} else {
				throw new Error(await previewResponse.text());
			}
		} catch (error) {
			console.error('Unable to fetch suggested controls preview', error);
			previewItems = reference_controls.map(
				(control) =>
					control?.name ||
					control?.reference_control?.str ||
					control?.reference_control?.name ||
					control?.ref_id ||
					''
			);
		}

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
					items: previewItems,
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
				count: previewItems.length,
				message: m.theFollowingControlsWillBeAddedColon()
			}),
			response: (r: boolean) => {
				createAppliedControlsLoading = r;
			}
		};
		modalStore.trigger(modal);
	}

	const requirementAssessmentForm = superForm(data.form, {
		dataType: 'json',
		invalidateAll: true,
		applyAction: true,
		resetForm: false,
		validators: zod(schema),
		taintedMessage: false,
		validationMethod: 'auto'
	});

	let mappingInference = $derived({
		sourceRequirementAssessment:
			data.requirementAssessment.mapping_inference.source_requirement_assessment,
		result: data.requirementAssessment.mapping_inference.result,
		annotation: ''
	});

	let requirementAssessmentsList: string[] = $hideSuggestions;

	let hideSuggestion = $state(
		requirementAssessmentsList.includes(data.requirementAssessment.id) ? true : false
	);

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

	let classesText = $derived(
		complianceResultColorMap[mappingInference.result] === '#000000' ? 'text-white' : ''
	);

	let group = $state(page.data.user.is_third_party ? 'evidences' : 'applied_controls');

	// Refresh AutompleteSelect to assign created applied control/evidence
	let refreshKey = $state(false);

	let formStore = $derived(requirementAssessmentForm.form);

	$effect(() => {
		if (form?.newControls) {
			refreshKey = !refreshKey;
			requirementAssessmentForm.form.update(
				(current: Record<string, any>) => ({
					...current,
					applied_controls: [...current.applied_controls, ...form?.newControls]
				}),
				{ taint: false }
			);
			form.newControls = undefined;
			console.debug('formStore', $formStore);
		}
	});

	$effect(() => {
		if (form?.newEvidence) {
			refreshKey = !refreshKey;
			requirementAssessmentForm.form.update(
				(current: Record<string, any>) => ({
					...current,
					evidences: [...current.evidences, form?.newEvidence]
				}),
				{ taint: false }
			);
			form.newEvidence = undefined;
			console.debug('formStore', $formStore);
		}
	});

	$effect(() => {
		if (form?.newSecurityException) {
			refreshKey = !refreshKey;
			requirementAssessmentForm.form.update(
				(current: Record<string, any>) => ({
					...current,
					security_exceptions: [...current.security_exceptions, form?.newSecurityException]
				}),
				{ taint: false }
			);
			form.newSecurityException = undefined;
			console.debug('formStore', $formStore);
		}
	});

	$effect(() => {
		if (createAppliedControlsLoading === true && form) createAppliedControlsLoading = false;
	});

	let computedScoreAndResult = $derived(
		computeRequirementScoreAndResult(data.requirementAssessment, $formStore.answers)
	);

	let computedResult = $derived(computedScoreAndResult.result);
	let computedScore = $derived(computedScoreAndResult.score);
</script>

{#if data.requirementAssessment.compliance_assessment.is_locked}
	<div
		class="alert bg-yellow-100 border border-yellow-300 text-yellow-800 px-4 py-3 rounded-lg shadow-sm mb-4"
	>
		<div class="flex items-center">
			<i class="fa-solid fa-lock text-yellow-600 mr-2"></i>
			<span class="font-medium">{m.lockedAssessment()}</span>
			<span class="ml-2 text-sm">{m.lockedRequirementAssessmentMessage()}</span>
		</div>
	</div>
{/if}
<div class="card space-y-2 p-4 bg-white shadow-sm">
	<div class="flex justify-between">
		<div class="flex">
			<span class="code left h-min">{data.requirement.urn}</span>
		</div>
		<a
			class="text-pink-500 hover:text-pink-400"
			href={complianceAssessmentURL}
			aria-label="Go to compliance assessment"><i class="fa-solid fa-turn-up"></i></a
		>
	</div>
	{#if data.requirement?.implementation_groups?.length > 0}
		<div class="mb-2">
			{#each data.requirement.implementation_groups as ig}
				<span class="badge bg-blue-100 mr-2">
					{getImplementationGroupName(ig)}
				</span>
			{/each}
		</div>
	{/if}
	{#if data.requirement.description}
		<div class="font-light text-lg card p-4 preset-tonal-primary">
			<h2 class="font-semibold text-base flex flex-row justify-between">
				<div>
					<i class="fa-solid fa-file-lines mr-2"></i>{m.description()}
				</div>
			</h2>
			<MarkdownRenderer content={data.requirement.description} />
		</div>
	{/if}
	{#if has_threats || has_reference_controls || annotation || mappingInference.result || typical_evidence}
		<div class="card p-4 preset-tonal-secondary text-sm flex flex-col justify-evenly cursor-auto">
			<h2 class="font-semibold text-base flex flex-row justify-between">
				<div>
					<i class="fa-solid fa-circle-info mr-2"></i>{m.additionalInformation()}
				</div>
				<button onclick={toggleSuggestions}>
					{#if !hideSuggestion}
						<i class="fa-solid fa-eye"></i>
					{:else}
						<i class="fa-solid fa-eye-slash"></i>
					{/if}
				</button>
			</h2>
			{#if !hideSuggestion}
				{#if has_threats || has_reference_controls}
					<div class="my-2 flex flex-col">
						<div class="flex-1">
							{#if reference_controls.length > 0}
								<p class="font-medium">
									<i class="fa-solid fa-gears"></i>
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
									<i class="fa-solid fa-gears"></i>
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
							<i class="fa-solid fa-pencil"></i>
							{m.annotation()}
						</p>
						<div class="py-1">
							<MarkdownRenderer content={annotation} />
						</div>
					</div>
				{/if}
				{#if typical_evidence}
					<div class="my-2">
						<p class="font-medium">
							<i class="fa-solid fa-pencil"></i>
							{m.typicalEvidence()}
						</p>
						<div class="py-1">
							<MarkdownRenderer content={typical_evidence} />
						</div>
					</div>
				{/if}
				{#if mappingInference.result}
					<div class="my-2">
						<p class="font-medium">
							<i class="fa-solid fa-link"></i>
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
			_form={requirementAssessmentForm}
			data={data.form}
			action="?/updateRequirementAssessment"
			{...rest}
		>
			{#snippet children({ form, data })}
				<div class="card shadow-lg bg-white">
					<Tabs
						value={group}
						onValueChange={(e) => {
							group = e.value;
						}}
					>
						<Tabs.List>
							{#if !page.data.user.is_third_party}
								<Tabs.Trigger value="applied_controls">{m.appliedControls()}</Tabs.Trigger>
							{/if}
							<Tabs.Trigger value="evidences">{m.evidences()}</Tabs.Trigger>
							<Tabs.Trigger value="security_exceptions">{m.securityExceptions()}</Tabs.Trigger>
							<Tabs.Indicator />
						</Tabs.List>
						<Tabs.Content value="applied_controls">
							<div class="flex items-center mb-2 px-2 text-xs space-x-2">
								<i class="fa-solid fa-info-circle"></i>
								<p>{m.requirementAppliedControlHelpText()}</p>
							</div>
							<div class="h-full flex flex-col space-y-2 rounded-container p-4">
								<span class="flex flex-row justify-end items-center space-x-2">
									{#if Object.hasOwn(page.data.user.permissions, 'add_appliedcontrol') && reference_controls.length > 0}
										<button
											class="btn text-gray-100 bg-linear-to-r from-fuchsia-500 to-pink-500 h-fit whitespace-normal"
											type="button"
											onclick={() => {
												modalConfirmCreateSuggestedControls(
													page.data.requirementAssessment.id,
													page.data.requirementAssessment.name,
													'?/createSuggestedControls'
												);
											}}
										>
											<span class="mr-2">
												{#if createAppliedControlsLoading}
													<Progress>
														<Progress.Circle class="[--size:--spacing(6)] -ml-2">
															<Progress.CircleTrack />
															<Progress.CircleRange class="stroke-white" />
														</Progress.Circle>
													</Progress>
												{:else}
													<i class="fa-solid fa-fire-extinguisher"></i>
												{/if}
											</span>
											{m.suggestControls()}
										</button>
									{/if}
									<button
										class="btn preset-filled-primary-500 self-end"
										onclick={modalMeasureCreateForm}
										type="button"
										><i class="fa-solid fa-plus mr-2"></i>{m.addAppliedControl()}</button
									>
								</span>
								{#key refreshKey}
									<AutocompleteSelect
										multiple
										{form}
										optionsEndpoint="applied-controls"
										optionsDetailedUrlParameters={[
											['scope_folder_id', page.data.requirementAssessment.folder.id]
										]}
										optionsExtraFields={[['folder', 'str']]}
										field="applied_controls"
										placeholder={m.appliedControlsPlaceholder()}
									/>
								{/key}
								<ModelTable
									baseEndpoint="/applied-controls?requirement_assessments={page.data
										.requirementAssessment.id}"
									source={page.data.tables['applied-controls']}
									hideFilters={true}
									URLModel="applied-controls"
									expectedCount={countMasked(page.data.requirementAssessment.applied_controls)}
								/>
							</div>
						</Tabs.Content>
						<Tabs.Content value="evidences">
							<div class="flex items-center mb-2 px-2 text-xs space-x-2">
								<i class="fa-solid fa-info-circle"></i>
								<p>{m.requirementEvidenceHelpText()}</p>
							</div>
							<div class="h-full flex flex-col space-y-2 rounded-container p-4">
								<span class="flex flex-row justify-end items-center">
									<button
										class="btn preset-filled-primary-500 self-end"
										onclick={modalEvidenceCreateForm}
										type="button"><i class="fa-solid fa-plus mr-2"></i>{m.addEvidence()}</button
									>
								</span>
								{#key refreshKey}
									<AutocompleteSelect
										multiple
										{form}
										optionsEndpoint="evidences"
										optionsExtraFields={[['folder', 'str']]}
										optionsDetailedUrlParameters={[
											['scope_folder_id', page.data.requirementAssessment.folder.id]
										]}
										field="evidences"
									/>
								{/key}
								<ModelTable
									source={page.data.tables['evidences']}
									hideFilters={true}
									URLModel="evidences"
									expectedCount={countMasked(page.data.requirementAssessment.evidences)}
									baseEndpoint="/evidences?requirement_assessments={page.data.requirementAssessment
										.id}"
								/>
							</div>
						</Tabs.Content>
						<Tabs.Content value="security_exceptions">
							<div class="h-full flex flex-col space-y-2 rounded-container p-4">
								<span class="flex flex-row justify-end items-center">
									<button
										class="btn preset-filled-primary-500 self-end"
										onclick={modalSecurityExceptionCreateForm}
										type="button"
										><i class="fa-solid fa-plus mr-2"></i>{m.addSecurityException()}</button
									>
								</span>
								{#key refreshKey}
									<AutocompleteSelect
										multiple
										{form}
										optionsEndpoint="security-exceptions"
										optionsExtraFields={[['folder', 'str']]}
										field="security_exceptions"
									/>
								{/key}
								<ModelTable
									source={page.data.tables['security-exceptions']}
									hideFilters={true}
									URLModel="security-exceptions"
									expectedCount={countMasked(page.data.requirementAssessment.security_exceptions)}
									baseEndpoint="/security-exceptions?requirement_assessments={page.data
										.requirementAssessment.id}"
								/>
							</div>
						</Tabs.Content>
					</Tabs>
				</div>
				<HiddenInput {form} field="folder" />
				<HiddenInput {form} field="requirement" />
				<HiddenInput {form} field="compliance_assessment" />
				<HiddenInput {form} field="nextRequirementAssessmentId" />
				<div class="flex flex-col my-8 space-y-6">
					{#if page.data.requirementAssessment.requirement.questions != null && Object.keys(page.data.requirementAssessment.requirement.questions).length !== 0}
						<Question
							{form}
							field="answers"
							questions={page.data.requirementAssessment.requirement.questions}
							label={m.questionSingular()}
						/>
					{/if}
					{#if page.data.requirementAssessment.compliance_assessment.progress_status_enabled}
						<Select
							{form}
							options={page.data.model.selectOptions['status']}
							field="status"
							label={m.status()}
							helpText={m.requirementAssessmentStatusHelpText()}
						/>
					{/if}
					{#if computedResult}
						<p class="flex flex-row items-center space-x-4">
							<span class="font-medium">{m.result()}</span>
							<span
								class="badge text-sm font-semibold"
								style="background-color: {complianceResultColorMap[
									computedResult || 'not_assessed'
								] || '#ddd'}"
							>
								{safeTranslate(computedResult || 'not_assessed')}
							</span>
						</p>
					{:else}
						<Select
							{form}
							options={page.data.model.selectOptions['result']}
							field="result"
							label={m.result()}
							helpText={m.requirementAssessmentResultHelpText()}
						/>
					{/if}
					{#if page.data.requirementAssessment.compliance_assessment.extended_result_enabled}
						<Select
							{form}
							options={page.data.model.selectOptions['extended_result']}
							field="extended_result"
							label={m.extendedResult()}
							helpText={m.extendedResultHelpText()}
						/>
					{/if}
					{#if computedScore !== null}
						<div class="flex flex-row items-center space-x-4">
							<span class="font-medium">{m.score()}</span>
							<div class="shrink-0 relative">
								<Progress
									value={formatScoreValue(
										computedScore || 0,
										page.data.compliance_assessment_score.max_score
									)}
									min={0}
									max={100}
								>
									<Progress.Circle class="[--size:--spacing(10)]">
										<Progress.CircleTrack />
										<Progress.CircleRange
											class={displayScoreColor(
												computedScore,
												page.data.compliance_assessment_score.max_score
											)}
										/>
									</Progress.Circle>
									<div class="absolute inset-0 flex items-center justify-center">
										<span class="text-xs font-bold">{computedScore}</span>
									</div>
								</Progress>
							</div>
						</div>
					{:else if data.result !== 'not_applicable'}
						<div class="flex flex-col">
							<Score
								{form}
								min_score={page.data.compliance_assessment_score.min_score}
								max_score={page.data.compliance_assessment_score.max_score}
								scores_definition={page.data.compliance_assessment_score.scores_definition}
								field="score"
								label={page.data.compliance_assessment_score.show_documentation_score
									? m.implementationScore()
									: m.score()}
								disabled={!data.is_scored}
							>
								{#snippet left()}
									<div>
										<Checkbox
											{form}
											field="is_scored"
											label={''}
											helpText={m.scoringHelpText()}
											checkboxComponent="switch"
											classes="h-full flex flex-row items-center justify-center my-1"
											classesContainer="h-full flex flex-row items-center space-x-4"
										/>
									</div>
								{/snippet}
							</Score>
						</div>
						{#if page.data.compliance_assessment_score.show_documentation_score}
							<Score
								{form}
								min_score={page.data.compliance_assessment_score.min_score}
								max_score={page.data.compliance_assessment_score.max_score}
								scores_definition={page.data.compliance_assessment_score.scores_definition}
								field="documentation_score"
								label={m.documentationScore()}
								isDoc={true}
								disabled={!data.is_scored}
							/>
						{/if}
					{/if}

					<MarkdownField {form} field="observation" label="Observation" />
				</div>
				<div
					class="flex flex-row justify-between space-x-4 sticky bottom-0 backdrop-blur-sm pt-4 pb-2 border-t border-slate-200"
				>
					<button
						class="btn bg-gray-400 text-white font-semibold w-full"
						type="button"
						onclick={cancel}>{m.cancel()}</button
					>
					<button
						class="btn preset-filled-secondary-500 font-semibold w-full"
						data-testid="save-no-continue-button"
						type="submit"
						onclick={() =>
							form.form.update((data) => {
								return { ...data, noRedirect: true };
							})}>{m.saveAndContinue()}</button
					>
					<button
						class="btn preset-filled-primary-500 font-semibold w-full"
						data-testid="save-button"
						type="submit"
						>{page.data.nextRequirementAssessmentId ? m.saveAndNext() : m.save()}</button
					>
				</div>
			{/snippet}
		</SuperForm>
	</div>
</div>
