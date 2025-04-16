<script lang="ts">
	import { page } from '$app/stores';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import Score from '$lib/components/Forms/Score.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import UpdateModal from '$lib/components/Modals/UpdateModal.svelte';
	import {
		complianceResultTailwindColorMap,
		complianceStatusTailwindColorMap
	} from '$lib/utils/constants';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import {
		Accordion,
		AccordionItem,
		getModalStore,
		RadioGroup,
		RadioItem,
		SlideToggle,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '@skeletonlabs/skeleton';
	import { superForm } from 'sveltekit-superforms';
	import type { Actions, PageData } from './$types';
	import { ProgressRadial } from '@skeletonlabs/skeleton';
	import { displayScoreColor } from '$lib/utils/helpers';
	import { complianceResultColorMap } from '$lib/utils/constants';

	export let data: PageData;
	export let form: Actions;
	/** Is the page used for shallow routing? */
	export let shallow = false;

	export let actionPath: string = '';
	export let questionnaireOnly: boolean = false;
	export let assessmentOnly: boolean = false;
	export let invalidateAll: boolean = true;

	const result_options = [
		{ id: 'not_assessed', label: m.notAssessed() },
		{ id: 'non_compliant', label: m.nonCompliant() },
		{ id: 'partially_compliant', label: m.partiallyCompliant() },
		{ id: 'compliant', label: m.compliant() },
		{ id: 'not_applicable', label: m.notApplicable() }
	];
	const status_options = [
		{ id: 'to_do', label: m.toDo() },
		{ id: 'in_progress', label: m.inProgress() },
		{ id: 'in_review', label: m.inReview() },
		{ id: 'done', label: m.done() }
	];

	const requirementHashmap = Object.fromEntries(
		data.requirements.map((requirement) => [requirement.id, requirement])
	);

	// Initialize hide suggestion state
	let hideSuggestionHashmap: Record<string, boolean> = {};
	data.requirement_assessments.forEach((ra) => {
		hideSuggestionHashmap[ra.id] = true;
	});

	$: createdEvidence = form?.createdEvidence;

	// Memoized title function
	const titleMap = new Map();
	function getTitle(requirementAssessment) {
		if (titleMap.has(requirementAssessment.id)) {
			return titleMap.get(requirementAssessment.id);
		}
		const requirement =
			requirementHashmap[requirementAssessment.requirement] ?? requirementAssessment;
		const result = requirement.display_short ? requirement.display_short : (requirement.name ?? '');
		titleMap.set(requirementAssessment.id, result);
		return result;
	}

	// Function to update requirement assessments, the data argument contain fields as keys and the associated values as values.
	async function updateBulk(
		requirementAssessment,
		data: { [key: string]: string | number | boolean | null }
	) {
		const form = document.getElementById(`tableModeForm-${requirementAssessment.id}`);
		const formData = {
			...data,
			id: requirementAssessment.id
		};
		const res = await fetch(form.action, {
			method: 'POST',
			body: JSON.stringify(formData)
		});
		return res;
	}

	// Function to update requirement assessments
	async function update(
		requirementAssessment,
		field: string,
		answers: {
			urn: { value: string | string[] };
		} | null = null
	) {
		const value = answers ? requirementAssessment.answers : requirementAssessment[field];
		await updateBulk(requirementAssessment, {
			[field]: value
		});

		// Update requirementAssessment.updateForm.data with the specified field and value
		if (requirementAssessment.updateForm && requirementAssessment.updateForm.data) {
			requirementAssessment.updateForm.data[field] = value;
		}
	}

	// Memoized color function
	const colorCache = new Map();
	function addColor(result: string, map: Record<string, string>) {
		const cacheKey = `${result}-${JSON.stringify(map)}`;
		if (colorCache.has(cacheKey)) {
			return colorCache.get(cacheKey);
		}
		const color = map[result];
		colorCache.set(cacheKey, color);
		return color;
	}

	let questionnaireMode = questionnaireOnly
		? true
		: assessmentOnly
			? false
			: $page.data.user.is_third_party
				? true
				: false;

	const modalStore: ModalStore = getModalStore();

	function modalEvidenceCreateForm(createform): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: createform,
				formAction: `${actionPath}?/createEvidence`,
				invalidateAll: invalidateAll,
				model: data.evidenceModel,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: safeTranslate('add-' + data.evidenceModel.localName)
		};
		modalStore.trigger(modal);
	}

	let addedEvidence = 0;

	$: if (createdEvidence && shallow) {
		const requirement = data.requirements.find((ra) => ra.id === createdEvidence.requirements[0]);
		if (requirement) {
			requirement.evidences.push({
				str: createdEvidence.name,
				id: createdEvidence.id
			});
			createdEvidence = undefined;
			addedEvidence += 1;
		}
	}

	const requirementAssessmentScores = Object.fromEntries(
		data.requirement_assessments.map((requirement) => {
			return [requirement.id, [requirement.is_scored, requirement.score]];
		})
	);

	async function updateScore(requirementAssessment) {
		const isScored = requirementAssessment.is_scored;
		const score = requirementAssessment.score;
		const documentationScore = requirementAssessment.documentation_score;
		requirementAssessmentScores[requirementAssessment.id] = [isScored, score, documentationScore];
		setTimeout(async () => {
			const currentScoreValue = requirementAssessmentScores[requirementAssessment.id];
			if (
				isScored === currentScoreValue[0] &&
				score === currentScoreValue[1] &&
				documentationScore === currentScoreValue[2]
			) {
				await updateBulk(requirementAssessment, {
					is_scored: isScored,
					score: score,
					documentation_score: documentationScore
				});
			}
		}, 500); // There must be 500ms without a score change for a request to be sent and modify the score of the RequirementAsessment in the backend
	}

	function modalUpdateForm(requirementAssessment): void {
		const modalComponent: ModalComponent = {
			ref: UpdateModal,
			props: {
				form: requirementAssessment.updateForm,
				model: requirementAssessment.updatedModel,
				object: requirementAssessment.object,
				formAction: '?/update&id=' + requirementAssessment.id,
				context: 'selectEvidences'
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: getTitle(requirementAssessment)
		};
		modalStore.trigger(modal);
	}

	function toggleSuggestion(requirementAssessmentId) {
		hideSuggestionHashmap[requirementAssessmentId] =
			!hideSuggestionHashmap[requirementAssessmentId];
	}

	function getClassesText(mappingInferenceResult) {
		return complianceResultColorMap[mappingInferenceResult] === '#000000' ? 'text-white' : '';
	}
	// Create separate superForm instances for each requirement assessment
	let scoreForms = {};
	let docScoreForms = {};
	let isScoredForms = {};
	$: {
		// Initialize the form instances
		data.requirement_assessments.forEach((requirementAssessment, index) => {
			const id = requirementAssessment.id;
			if (!scoreForms[id]) {
				scoreForms[id] = superForm(requirementAssessment.scoreForm, {
					id: `requirement-score-${id}-${index}`
				});
			}
			if (!docScoreForms[id]) {
				docScoreForms[id] = superForm(requirementAssessment.scoreForm, {
					id: `requirement-documentation-score-${id}-${index}`
				});
			}
			if (!isScoredForms[id]) {
				isScoredForms[id] = superForm(requirementAssessment.scoreForm, {
					id: `requirement-is-scored-${id}-${index}`
				});
			}
		});
	}
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<div
		class="card px-6 py-4 bg-white flex flex-col justify-evenly shadow-lg w-full h-full space-y-2"
	>
		{#if !(questionnaireOnly ? !assessmentOnly : assessmentOnly)}
			<div
				class="sticky top-0 p-2 z-10 card bg-white items-center justify-evenly flex flex-row w-full"
			>
				<a
					href="/compliance-assessments/{data.compliance_assessment.id}"
					class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
				>
					<i class="fa-solid fa-arrow-left" />
					<p class="">{m.goBackToAudit()} {data.compliance_assessment.name}</p>
				</a>
				<div class="flex items-center justify-center space-x-4">
					{#if questionnaireMode}
						<p class="font-bold text-sm">{m.assessmentMode()}</p>
					{:else}
						<p class="font-bold text-sm text-green-500">{m.assessmentMode()}</p>
					{/if}
					<SlideToggle
						name="questionnaireToggle"
						class="flex flex-row items-center justify-center"
						active="bg-primary-500"
						background="bg-green-500"
						bind:checked={questionnaireMode}
						on:click={() => (questionnaireMode = !questionnaireMode)}
					>
						{#if questionnaireMode}
							<p class="font-bold text-sm text-primary-500">{m.questionnaireMode()}</p>
						{:else}
							<p class="font-bold text-sm">{m.questionnaireMode()}</p>
						{/if}
					</SlideToggle>
				</div>
			</div>
		{/if}
		{#each data.requirement_assessments as requirementAssessment, i}
			<div class="w-2"></div>

			<span class="relative flex justify-center py-4">
				<div
					class="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-transparent bg-gradient-to-r from-transparent via-gray-500 to-transparent opacity-75"
				></div>

				<span class="relative z-10 bg-white px-6 text-orange-600 font-semibold text-xl z-auto">
					{getTitle(requirementAssessment)}
				</span>
			</span>
			<div class="h-2"></div>
			<div
				class="flex flex-col items-center justify-center border px-4 py-2 shadow rounded-xl space-y-2"
			>
				{#if requirementAssessment.description}
					<div class="flex w-full font-semibold">
						{requirementAssessment.description}
					</div>
				{/if}
				{#if requirementAssessment.assessable}
					{#if data.requirements[i].annotation || requirementAssessment.mapping_inference.result}
						<div
							class="card p-4 variant-glass-primary text-sm flex flex-col justify-evenly cursor-auto w-full"
						>
							<h2 class="font-semibold text-lg flex flex-row justify-between">
								<div>
									<i class="fa-solid fa-circle-info mr-2" />{m.additionalInformation()}
								</div>
								<button on:click={() => toggleSuggestion(requirementAssessment.id)}>
									{#if !hideSuggestionHashmap[requirementAssessment.id]}
										<i class="fa-solid fa-eye" />
									{:else}
										<i class="fa-solid fa-eye-slash" />
									{/if}
								</button>
							</h2>
							{#if !hideSuggestionHashmap[requirementAssessment.id]}
								{#if data.requirements[i].annotation}
									<div class="my-2">
										<p class="font-medium">
											<i class="fa-solid fa-pencil" />
											{m.annotation()}
										</p>
										<p class="whitespace-pre-line py-1">
											{data.requirements[i].annotation}
										</p>
									</div>
								{/if}
								{#if requirementAssessment.mapping_inference.result}
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
														href="/requirement-assessments/{requirementAssessment.mapping_inference
															.source_requirement_assessment.id}"
													>
														{requirementAssessment.mapping_inference.source_requirement_assessment
															.str}
													</a>
												</p>
												<p class="whitespace-pre-line py-1">
													<span class="italic">{m.coverageColon()}</span>
													<span class="badge h-fit">
														{safeTranslate(
															requirementAssessment.mapping_inference.source_requirement_assessment
																.coverage
														)}
													</span>
												</p>
												{#if requirementAssessment.mapping_inference.source_requirement_assessment.is_scored}
													<p class="whitespace-pre-line py-1">
														<span class="italic">{m.scoreSemiColon()}</span>
														<span class="badge h-fit">
															{safeTranslate(
																requirementAssessment.mapping_inference
																	.source_requirement_assessment.score
															)}
														</span>
													</p>
												{/if}
												<p class="whitespace-pre-line py-1">
													<span class="italic">{m.suggestionColon()}</span>
													<span
														class="badge {getClassesText(
															requirementAssessment.mapping_inference.result
														)} h-fit"
														style="background-color: {complianceResultColorMap[
															requirementAssessment.mapping_inference.result
														]};"
													>
														{safeTranslate(requirementAssessment.mapping_inference.result)}
													</span>
												</p>
												{#if requirementAssessment.mapping_inference.annotation}
													<p class="whitespace-pre-line py-1">
														<span class="italic">{m.annotationColon()}</span>
														{requirementAssessment.mapping_inference.annotation}
													</p>
												{/if}
											</li>
										</ul>
									</div>
								{/if}
							{/if}
						</div>
					{/if}

					<form
						class="flex flex-col space-y-2 items-center justify-evenly w-full"
						id="tableModeForm-{requirementAssessment.id}"
						action="{actionPath}?/updateRequirementAssessment"
						method="post"
					>
						{#if !questionnaireMode}
							<div class="flex flex-row w-full space-x-2 my-4">
								<div class="flex flex-col items-center w-1/2">
									<p class="flex items-center font-semibold text-blue-600 italic">{m.status()}</p>
									<RadioGroup class="w-full flex-wrap items-center">
										{#each status_options as option}
											<RadioItem
												class="h-full"
												id={option.id}
												active={addColor(
													requirementAssessment.status,
													complianceStatusTailwindColorMap
												)}
												value={option.id}
												bind:group={requirementAssessment.status}
												name="status"
												on:click={async () => {
													const newStatus =
														requirementAssessment.status === option.id ? 'to_do' : option.id;
													requirementAssessment.status = newStatus;
													await update(requirementAssessment, 'status');
												}}>{option.label}</RadioItem
											>
										{/each}
									</RadioGroup>
								</div>
								<div class="flex flex-col items-center w-1/2">
									<p class="flex items-center font-semibold text-purple-600 italic">
										{m.result()}
									</p>
									<RadioGroup class="w-full flex-wrap items-center">
										{#each result_options as option}
											<RadioItem
												class="h-full"
												active={addColor(
													requirementAssessment.result,
													complianceResultTailwindColorMap
												)}
												id={option.id}
												value={option.id}
												bind:group={requirementAssessment.result}
												name="result"
												on:click={async () => {
													const newResult =
														requirementAssessment.result === option.id ? 'not_assessed' : option.id;
													requirementAssessment.result = newResult;
													await update(requirementAssessment, 'result'); // Update result for both select and deselect
												}}
												>{option.label}
											</RadioItem>
										{/each}
									</RadioGroup>
								</div>
							</div>
						{/if}
						{#if requirementAssessment.requirement.questions != null && Object.keys(requirementAssessment.requirement.questions).length !== 0}
							<div class="flex flex-col w-full space-y-2">
								{#each Object.entries(requirementAssessment.requirement.questions) as [urn, question]}
									<li class="flex flex-col space-y-2 rounded-xl">
										<p>{question.text} ({safeTranslate(question.type)})</p>
										{#if shallow}
											{#if Array.isArray(requirementAssessment.answers[urn])}
												{#each requirementAssessment.answers[urn] as answerUrn}
													{#if question.choices.find((choice) => choice.urn === answerUrn)}
														<p class="text-primary-500 font-semibold">
															{question.choices.find((choice) => choice.urn === answerUrn).value}
														</p>
													{:else}
														<p class="text-primary-500 font-semibold">
															{answerUrn}
														</p>
													{/if}
												{/each}
											{:else if question.choices.find((choice) => choice.urn === requirementAssessment.answers[urn])}
												<p class="text-primary-500 font-semibold">
													{question.choices.find(
														(choice) => choice.urn === requirementAssessment.answers[urn]
													).value}
												</p>
											{:else}
												<p class="text-gray-400 italic">{m.noAnswer()}</p>
											{/if}
										{:else if question.type === 'unique_choice'}
											<RadioGroup
												class="flex-col"
												active="variant-filled-primary"
												hover="hover:variant-soft-primary"
											>
												{#each question.choices as option}
													<RadioItem
														class="shadow-md flex"
														bind:group={requirementAssessment.answers[urn]}
														name="question"
														value={option.urn}
														on:click={async () => {
															const newAnswer =
																requirementAssessment.answers[urn] === option.urn
																	? null
																	: option.urn;
															requirementAssessment.answers[urn] = newAnswer;
															await update(
																requirementAssessment,
																'answers',
																requirementAssessment.answers
															);
														}}
														><span class="text-left">{option.value}</span>
													</RadioItem>
												{/each}
											</RadioGroup>
										{:else if question.type === 'multiple_choice'}
											<div
												class="flex flex-col gap-1 p-1 bg-surface-200-700-token border-token border-surface-400-500-token rounded-token"
											>
												{#each question.choices as option}
													<button
														type="button"
														name="question"
														class="shadow-md p-1
															{requirementAssessment.answers[urn] && requirementAssessment.answers[urn].includes(option.urn)
															? 'variant-filled-primary rounded-token'
															: 'hover:variant-soft-primary bg-surface-200-700-token rounded-token'}"
														on:click={async () => {
															// Initialize the array if it hasn't been already.
															if (!Array.isArray(requirementAssessment.answers[urn])) {
																requirementAssessment.answers[urn] = [];
															}
															// Toggle the option's selection
															if (requirementAssessment.answers[urn].includes(option.urn)) {
																requirementAssessment.answers[urn] = requirementAssessment.answers[
																	urn
																].filter((val) => val !== option.urn);
															} else {
																requirementAssessment.answers[urn] = [
																	...requirementAssessment.answers[urn],
																	option.urn
																];
															}
															// Update the requirement assessment with the new answers
															await update(
																requirementAssessment,
																'answers',
																requirementAssessment.answers
															);
														}}
													>
														{option.value}
													</button>
												{/each}
											</div>
										{:else if question.type === 'date'}
											<input
												type="date"
												placeholder=""
												class="input w-fit"
												bind:value={requirementAssessment.answers[urn]}
												on:change={async () =>
													await update(
														requirementAssessment,
														'answers',
														requirementAssessment.answers
													)}
												{...$$restProps}
											/>
										{:else}
											<textarea
												placeholder=""
												class="input w-full"
												bind:value={requirementAssessment.answers[urn]}
												on:keydown={(event) => event.key === 'Enter' && event.preventDefault()}
												on:change={async () =>
													await update(
														requirementAssessment,
														'answers',
														requirementAssessment.answers
													)}
												{...$$restProps}
											/>
										{/if}
									</li>
								{/each}
							</div>
						{/if}
						<div class="flex flex-col w-full place-items-center">
							{#if !shallow}
								<Score
									form={scoreForms[requirementAssessment.id]}
									min_score={data.compliance_assessment.min_score}
									max_score={data.compliance_assessment.max_score}
									scores_definition={data.compliance_assessment.scores_definition}
									field="score"
									label={data.compliance_assessment.show_documentation_score
										? m.implementationScore()
										: m.score()}
									styles="w-full p-1"
									bind:score={requirementAssessment.score}
									on:change={async () => await updateScore(requirementAssessment)}
									disabled={!requirementAssessment.is_scored ||
										requirementAssessment.result === 'not_applicable'}
								>
									<div slot="left">
										<Checkbox
											form={isScoredForms[requirementAssessment.id]}
											field="is_scored"
											label={''}
											helpText={m.scoringHelpText()}
											checkboxComponent="switch"
											class="h-full flex flex-row items-center justify-center my-1"
											classesContainer="h-full flex flex-row items-center space-x-4"
											on:change={async () => {
												requirementAssessment.is_scored = !requirementAssessment.is_scored;
												await update(requirementAssessment, 'is_scored');
											}}
										/>
									</div>
								</Score>
								{#if data.compliance_assessment.show_documentation_score}
									<Score
										form={docScoreForms[requirementAssessment.id]}
										min_score={data.compliance_assessment.min_score}
										max_score={data.compliance_assessment.max_score}
										field="documentation_score"
										label={m.documentationScore()}
										styles="w-full p-1"
										bind:score={requirementAssessment.documentation_score}
										on:change={async () => await updateScore(requirementAssessment)}
										disabled={!requirementAssessment.is_scored ||
											requirementAssessment.result === 'not_applicable'}
									/>
								{/if}
							{:else if data.compliance_assessment.show_documentation_score && requirementAssessment.is_scored}
								<div class="flex flex-row items-center space-x-2 w-full">
									<span>{m.implementationScoreResult()}</span>
									<ProgressRadial
										stroke={100}
										meter={displayScoreColor(
											requirementAssessment.score,
											data.compliance_assessment.max_score
										)}
										font={150}
										value={(requirementAssessment.score * 100) /
											data.compliance_assessment.max_score}
										width="w-10"
									>
										{requirementAssessment.score ?? '--'}
									</ProgressRadial>
									<span>{m.documentationScoreResult()}</span>
									<ProgressRadial
										stroke={100}
										meter={displayScoreColor(
											requirementAssessment.documentation_score,
											data.compliance_assessment.max_score
										)}
										font={150}
										value={(requirementAssessment.documentation_score * 100) /
											data.compliance_assessment.max_score}
										width="w-10"
									>
										{requirementAssessment.documentation_score ?? '--'}
									</ProgressRadial>
								</div>
							{:else if requirementAssessment.is_scored}
								<div class="flex flex-row items-center space-x-2 w-full">
									<span>{m.scoreResult()}</span>
									<ProgressRadial
										stroke={100}
										meter={displayScoreColor(
											requirementAssessment.score,
											data.compliance_assessment.max_score
										)}
										font={150}
										value={(requirementAssessment.score * 100) /
											data.compliance_assessment.max_score}
										width="w-10"
									>
										{requirementAssessment.score ?? '--'}
									</ProgressRadial>
								</div>
							{/if}
							<Accordion regionCaret="flex">
								{#if shallow}
									{#if requirementAssessment.observation}
										<p class="text-primary-500">{requirementAssessment.observation}</p>
									{:else}
										<p class="text-gray-400 italic">{m.noObservation()}</p>
									{/if}
								{:else}
									<AccordionItem caretOpen="rotate-0" caretClosed="-rotate-90">
										<svelte:fragment slot="summary"
											><p class="flex">{m.observation()}</p></svelte:fragment
										>
										<svelte:fragment slot="content">
											<div>
												<textarea
													placeholder=""
													class="input w-full"
													bind:value={requirementAssessment.observation}
													on:keydown={(event) => event.key === 'Enter' && event.preventDefault()}
												/>
												{#if requirementAssessment.observationBuffer !== requirementAssessment.observation}
													<button
														class="rounded-md w-8 h-8 border shadow-lg hover:bg-green-300 hover:text-green-500 duration-300"
														on:click={async () => {
															await update(requirementAssessment, 'observation');
															requirementAssessment.observationBuffer =
																requirementAssessment.observation;
														}}
														type="button"
													>
														<i class="fa-solid fa-check opacity-70"></i>
													</button>
													<button
														class="rounded-md w-8 h-8 border shadow-lg hover:bg-red-300 hover:text-red-500 duration-300"
														on:click={() =>
															(requirementAssessment.observation =
																requirementAssessment.observationBuffer)}
														type="button"
													>
														<i class="fa-solid fa-xmark opacity-70"></i>
													</button>
												{/if}
											</div>
										</svelte:fragment>
									</AccordionItem>
								{/if}
								{#if requirementAssessment.evidences.length === 0 && shallow}
									<p class="text-gray-400 italic">{m.noEvidences()}</p>
								{:else}
									<AccordionItem caretOpen="rotate-0" caretClosed="-rotate-90">
										<svelte:fragment slot="summary"
											><p class="flex items-center space-x-2">
												<span>{m.evidence()}</span>
												{#key addedEvidence}
													{#if requirementAssessment.evidences != null}
														<span class="badge variant-soft-primary"
															>{requirementAssessment.evidences.length}</span
														>
													{/if}
												{/key}
											</p></svelte:fragment
										>
										<svelte:fragment slot="content">
											<div class="flex flex-row space-x-2 items-center">
												{#if !shallow}
													<button
														class="btn variant-filled-primary self-start"
														on:click={() =>
															modalEvidenceCreateForm(requirementAssessment.evidenceCreateForm)}
														type="button"
														><i class="fa-solid fa-plus mr-2" />{m.addEvidence()}</button
													>
													<button
														class="btn variant-filled-secondary self-start"
														type="button"
														on:click={() => modalUpdateForm(requirementAssessment)}
														><i class="fa-solid fa-hand-pointer mr-2"></i>{m.selectEvidence()}
													</button>
												{/if}
											</div>
											<div class="flex flex-wrap space-x-2 items-center">
												{#key addedEvidence}
													{#each requirementAssessment.evidences as evidence}
														<p class="p-2">
															<a
																class="text-primary-700 hover:text-primary-500"
																href="/evidences/{evidence.id}"
																><i class="fa-solid fa-file mr-2"></i>{evidence.str}</a
															>
														</p>
													{/each}
												{/key}
											</div>
										</svelte:fragment>
									</AccordionItem>
								{/if}
							</Accordion>
						</div>
					</form>
				{/if}
			</div>
		{/each}
	</div>
</div>
