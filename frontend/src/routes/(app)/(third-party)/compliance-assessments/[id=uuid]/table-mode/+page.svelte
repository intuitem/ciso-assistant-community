<script lang="ts">
	import { run } from 'svelte/legacy';

	import { page } from '$app/state';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import Question from '$lib/components/Forms/Question.svelte';
	import RadioGroup from '$lib/components/Forms/RadioGroup.svelte';
	import Score from '$lib/components/Forms/Score.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import TableMarkdownField from '$lib/components/Forms/TableMarkdownField.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import UpdateModal from '$lib/components/Modals/UpdateModal.svelte';
	import {
		complianceResultColorMap,
		complianceResultTailwindColorMap,
		complianceStatusTailwindColorMap
	} from '$lib/utils/constants';
	import { displayScoreColor, formatScoreValue } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { Accordion, ProgressRing, Switch } from '@skeletonlabs/skeleton-svelte';
	import { superForm, type SuperForm } from 'sveltekit-superforms';
	import type { Actions, PageData } from './$types';
	import TableOfContents from '$lib/components/TableOfContents/TableOfContents.svelte';
	import { generateTocFromElements, type TocItem } from '$lib/utils/toc';
	import { onMount } from 'svelte';
	import { invalidateAll } from '$app/navigation';

	interface Props {
		data: PageData;
		form: Actions;
		/** Is the page used for shallow routing? */
		shallow?: boolean;
		actionPath?: string;
		questionnaireOnly?: boolean;
		invalidateAllBool?: boolean;
		[key: string]: any;
	}

	let {
		data,
		form,
		shallow = false,
		actionPath = '',
		questionnaireOnly = false,
		invalidateAllBool = true
	}: Props = $props();

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
		data.requirements.map((requirement: Record<string, any>) => [requirement.id, requirement])
	);

	// Initialize hide suggestion state
	let hideSuggestionHashmap: Record<string, boolean> = $state({});
	let requirementAssessments = $derived(data.requirement_assessments);
	let complianceAssessment = $derived(data.compliance_assessment);

	const hasQuestions = $derived(
		requirementAssessments.some(
			(requirementAssessment) => requirementAssessment.requirement.questions
		)
	);

	// svelte-ignore state_referenced_locally
	requirementAssessments.forEach((ra) => {
		hideSuggestionHashmap[ra.id] = false;
	});

	// Memoized title function
	const titleMap = new Map();
	function getTitle(requirementAssessment: Record<string, any>) {
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
		requirementAssessment: Record<string, any>,
		data: { [key: string]: string | number | boolean | null }
	) {
		const form = document.getElementById(
			`tableModeForm-${requirementAssessment.id}`
		) as HTMLFormElement;
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
		requirementAssessment: Record<string, any>,
		field: string,
		answers: {
			urn: { value: string | string[] };
		} | null = null
	) {
		const value = answers ? requirementAssessment.answers : requirementAssessment[field];
		await updateBulk(requirementAssessment, {
			[field]: value
		});

		if (invalidateAll) {
			await invalidateAll();
		}

		// Update requirementAssessment.updateForm.data with the specified field and value
		if (requirementAssessment.updateForm && requirementAssessment.updateForm.data) {
			requirementAssessment.updateForm.data[field] = value;
		}
	}

	let questionnaireMode = $state(
		questionnaireOnly ? true : !hasQuestions ? false : page.data.user.is_third_party ? true : false
	);

	const modalStore: ModalStore = getModalStore();

	function modalEvidenceCreateForm(createform: SuperForm<any>): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: createform,
				formAction: `${actionPath}?/createEvidence`,
				invalidateAll: invalidateAllBool,
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

	let addedEvidence = $state(0);

	const requirementAssessmentScores = Object.fromEntries(
		// svelte-ignore state_referenced_locally
		requirementAssessments.map((requirement) => {
			return [requirement.id, [requirement.is_scored, requirement.score]];
		})
	);

	async function updateScore(requirementAssessment: Record<string, any>) {
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

	function modalUpdateForm(requirementAssessment: Record<string, any>): void {
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

	function toggleSuggestion(requirementAssessmentId: string) {
		hideSuggestionHashmap[requirementAssessmentId] =
			!hideSuggestionHashmap[requirementAssessmentId];
	}

	function getClassesText(mappingInferenceResult: string) {
		return complianceResultColorMap[mappingInferenceResult] === '#000000' ? 'text-white' : '';
	}
	// Create separate superForm instances for each requirement assessment
	let scoreForms = $state({});
	let docScoreForms = $state({});
	let isScoredForms = $state({});

	run(() => {
		// Initialize the form instances
		requirementAssessments.forEach((requirementAssessment, index) => {
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
	});

	const accordionItems: Record<string, ['' | 'observation' | 'evidence']> = $state(
		// svelte-ignore state_referenced_locally
		requirementAssessments.reduce((acc, requirementAssessment) => {
			const requirement =
				requirementHashmap[requirementAssessment.requirement] ?? requirementAssessment;
			return {
				...acc,
				[requirementAssessment.id]: ['']
			};
		})
	);

	let tocItems: TocItem[] = $state([]);
	let showToc = $state(true);
	// Generate TOC items from requirement assessments - only include title nodes
	$effect(() => {
		if (requirementAssessments.length > 0) {
			tocItems = requirementAssessments
				.filter((ra) => {
					// Only include non-assessable nodes, non empty title and depth <= 4
					const requirement = requirementHashmap[ra.requirement] ?? ra;
					if (ra.assessable || requirement.assessable) return false;

					const refId = requirement.ref_id ?? requirement.requirement?.ref_id;
					const name = requirement.name;

					const hasRefId = refId && refId.trim();
					const hasName = name && name.trim();
					if (!hasRefId && !hasName) return false;

					if (refId) {
						const parts = refId.split('.');
						if (parts.length > 4) return false;
					}

					return true;
				})
				.map((ra, index) => {
					const requirement = requirementHashmap[ra.requirement] ?? ra;

					// Safely access ref_id and name
					const refId = requirement.ref_id ?? requirement.requirement?.ref_id;
					const name = requirement.name;

					let title = '';
					if (name && name.trim()) {
						title = name.trim();
					} else if (refId && refId.trim()) {
						title = refId.trim();
					} else {
						title = `Section ${index + 1}`;
					}

					let level = 0;
					if (refId && refId.trim()) {
						const parts = refId.split('.');
						level = Math.max(0, parts.length - 1);
					}

					return {
						id: `requirement-${ra.id}`,
						title: title,
						level: Math.min(level, 4)
					};
				});
		}
	});
	onMount(() => {
		// Show TOC only if there are more than 3 requirements
		showToc = requirementAssessments.length > 3;
	});
</script>

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<TableOfContents
		items={tocItems}
		isVisible={showToc}
		position="right"
		className="hidden lg:block"
	/>
	<div
		class="card px-6 py-4 bg-white flex flex-col justify-evenly shadow-lg w-full h-full space-y-2"
	>
		<div
			class="sticky top-0 p-2 z-10 card bg-white items-center justify-evenly flex flex-row w-full"
		>
			{#if !(questionnaireOnly ? hasQuestions : !hasQuestions)}
				<div class="flex items-center justify-center space-x-4">
					{#if questionnaireMode}
						<p class="font-bold text-sm">{m.assessmentMode()}</p>
					{:else}
						<p class="font-bold text-sm text-green-500">{m.assessmentMode()}</p>
					{/if}
					<Switch
						name="questionnaireToggle"
						classes="flex flex-row items-center justify-center"
						controlActive="bg-primary-500"
						controlInactive="bg-green-500"
						onCheckedChange={(e) => {
							questionnaireMode = e.checked;
						}}
					>
						{#if questionnaireMode}
							<p class="font-bold text-sm text-primary-500">{m.questionnaireMode()}</p>
						{:else}
							<p class="font-bold text-sm">{m.questionnaireMode()}</p>
						{/if}
					</Switch>
				</div>
			{/if}
		</div>
		{#each requirementAssessments as requirementAssessment, i}
			<div class="w-2"></div>

			<span
				class="relative flex justify-center py-4"
				id="requirement-{requirementAssessment.id}"
				data-toc
				data-toc-title={getTitle(requirementAssessment)}
				data-toc-level="0"
			>
				<div
					class="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-transparent bg-linear-to-r from-transparent via-gray-500 to-transparent opacity-75"
				></div>

				<span class="relative z-10 bg-white px-6 text-orange-600 font-semibold text-xl">
					{getTitle(requirementAssessment)}
				</span>
			</span>
			<div class="h-2"></div>
			{#if requirementAssessment.description || requirementAssessment.assessable}
				<div
					class="flex flex-col items-center justify-center border px-4 py-2 shadow-sm rounded-xl space-y-2"
				>
					{#if requirementAssessment.description}
						<div class="card w-full font-light text-lg p-4 preset-tonal-primary">
							<h2 class="font-semibold text-base flex flex-row justify-between">
								<div>
									<i class="fa-solid fa-file-lines mr-2"></i>{m.description()}
								</div>
							</h2>
							<MarkdownRenderer content={requirementAssessment.description} />
						</div>
					{/if}
					{#if requirementAssessment.assessable}
						{#if data.requirements[i].annotation || data.requirements[i].typical_evidence || requirementAssessment.mapping_inference?.result}
							<div
								class="card p-4 preset-tonal-secondary text-sm flex flex-col justify-evenly cursor-auto w-full"
							>
								<h2 class="font-semibold text-base flex flex-row justify-between">
									<div>
										<i class="fa-solid fa-circle-info mr-2"></i>{m.additionalInformation()}
									</div>
									<button onclick={() => toggleSuggestion(requirementAssessment.id)}>
										{#if !hideSuggestionHashmap[requirementAssessment.id]}
											<i class="fa-solid fa-eye"></i>
										{:else}
											<i class="fa-solid fa-eye-slash"></i>
										{/if}
									</button>
								</h2>
								{#if !hideSuggestionHashmap[requirementAssessment.id]}
									{#if data.requirements[i].annotation}
										<div class="my-2">
											<p class="font-medium">
												<i class="fa-solid fa-pencil"></i>
												{m.annotation()}
											</p>
											<div class="py-1">
												<MarkdownRenderer content={data.requirements[i].annotation} />
											</div>
										</div>
									{/if}
									{#if data.requirements[i].typical_evidence}
										<div class="my-2">
											<p class="font-medium">
												<i class="fa-solid fa-pencil"></i>
												{m.typicalEvidence()}
											</p>
											<div class="py-1">
												<MarkdownRenderer content={data.requirements[i].typical_evidence} />
											</div>
										</div>
									{/if}
									{#if requirementAssessment.mapping_inference?.result}
										<div class="my-2">
											<p class="font-medium">
												<i class="fa-solid fa-link"></i>
												{m.mappingInference()}
											</p>
											<span class="text-xs text-gray-500"
												><i class="fa-solid fa-circle-info"></i>
												{m.mappingInferenceHelpText()}</span
											>
											<ul class="list-disc ml-4">
												<li>
													<p>
														<a
															class="anchor"
															href="/requirement-assessments/{requirementAssessment
																.mapping_inference.source_requirement_assessment.id}"
														>
															{requirementAssessment.mapping_inference.source_requirement_assessment
																.str}
														</a>
													</p>
													<p class="whitespace-pre-line py-1">
														<span class="italic">{m.coverageColon()}</span>
														<span class="badge h-fit">
															{safeTranslate(
																requirementAssessment.mapping_inference
																	.source_requirement_assessment.coverage
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
										<RadioGroup
											possibleOptions={status_options}
											key="id"
											labelKey="label"
											field="status"
											colorMap={complianceStatusTailwindColorMap}
											initialValue={requirementAssessment.status}
											onChange={(newValue) => {
												const newStatus =
													requirementAssessment.status === newValue ? 'to_do' : newValue;
												requirementAssessment.status = newStatus;
												update(requirementAssessment, 'status');
											}}
										/>
									</div>
									<div class="flex flex-col items-center w-1/2">
										<p class="flex items-center font-semibold text-purple-600 italic">
											{m.result()}
										</p>
										{#if complianceAssessment.framework.is_dynamic}
											<span
												class="badge text-sm font-semibold"
												style="background-color: {complianceResultColorMap[
													requirementAssessment.result
												] || '#ddd'}"
											>
												{safeTranslate(requirementAssessment.result)}
											</span>
										{:else}
											<RadioGroup
												possibleOptions={result_options}
												key="id"
												labelKey="label"
												field="result"
												colorMap={complianceResultTailwindColorMap}
												initialValue={requirementAssessment.result}
												onChange={(newValue) => {
													const newResult =
														requirementAssessment.result === newValue ? 'not_assessed' : newValue;
													requirementAssessment.result = newResult;
													update(requirementAssessment, 'result');
												}}
											/>
										{/if}
									</div>
								</div>
							{/if}
							{#if requirementAssessment.requirement.questions != null && Object.keys(requirementAssessment.requirement.questions).length !== 0}
								<div class="flex flex-col w-full space-y-2">
									<Question
										questions={requirementAssessment.requirement.questions}
										initialValue={requirementAssessment.answers}
										field="answers"
										{shallow}
										onChange={(urn, newAnswer) => {
											requirementAssessment.answers[urn] = newAnswer;
											update(requirementAssessment, 'answers', requirementAssessment.answers);
										}}
									/>
								</div>
							{/if}
							<div class="flex flex-col w-full place-items-center">
								{#if !shallow}
									{#if complianceAssessment.framework.is_dynamic}
										<div class="flex flex-row items-center space-x-4">
											<span class="font-medium">{m.score()}</span>
											<ProgressRing
												strokeWidth="20px"
												meterStroke={displayScoreColor(
													requirementAssessment.score,
													complianceAssessment.max_score
												)}
												value={formatScoreValue(
													requirementAssessment.score,
													complianceAssessment.max_score
												)}
												classes="shrink-0"
												size="size-10">{requirementAssessment.score}</ProgressRing
											>
										</div>
									{:else}
										<Score
											form={scoreForms[requirementAssessment.id]}
											min_score={complianceAssessment.min_score}
											max_score={complianceAssessment.max_score}
											scores_definition={data.scores.scores_definition}
											field="score"
											label={complianceAssessment.show_documentation_score
												? m.implementationScore()
												: m.score()}
											styles="w-full p-1"
											onChange={(newScore) => {
												requirementAssessment.score = newScore;
												updateScore(requirementAssessment);
											}}
											disabled={!requirementAssessment.is_scored ||
												requirementAssessment.result === 'not_applicable'}
										>
											{#snippet left()}
												<div>
													<Checkbox
														form={isScoredForms[requirementAssessment.id]}
														field="is_scored"
														label={''}
														helpText={m.scoringHelpText()}
														checkboxComponent="switch"
														classes="h-full flex flex-row items-center justify-center my-1"
														classesContainer="h-full flex flex-row items-center space-x-4"
														onChange={async () => {
															requirementAssessment.is_scored = !requirementAssessment.is_scored;
															await update(requirementAssessment, 'is_scored');
														}}
													/>
												</div>
											{/snippet}
										</Score>
										{#if complianceAssessment.show_documentation_score}
											<Score
												form={docScoreForms[requirementAssessment.id]}
												min_score={complianceAssessment.min_score}
												max_score={complianceAssessment.max_score}
												scores_definition={data.scores.scores_definition}
												field="documentation_score"
												label={m.documentationScore()}
												isDoc={true}
												styles="w-full p-1"
												onChange={(newScore) => {
													requirementAssessment.documentation_score = newScore;
													updateScore(requirementAssessment);
												}}
												disabled={!requirementAssessment.is_scored ||
													requirementAssessment.result === 'not_applicable'}
											/>
										{/if}
									{/if}
								{:else if complianceAssessment.show_documentation_score && requirementAssessment.is_scored}
									<div class="flex flex-row items-center space-x-2 w-full">
										<span>{m.implementationScoreResult()}</span>
										<ProgressRing
											strokeWidth="20px"
											meterStroke={displayScoreColor(
												requirementAssessment.score,
												complianceAssessment.max_score
											)}
											value={(requirementAssessment.score * 100) / complianceAssessment.max_score}
											size="size-10"
										>
											{requirementAssessment.score ?? '--'}
										</ProgressRing>
										<span>{m.documentationScoreResult()}</span>
										<ProgressRing
											strokeWidth="20px"
											meterStroke={displayScoreColor(
												requirementAssessment.documentation_score,
												complianceAssessment.max_score
											)}
											value={(requirementAssessment.documentation_score * 100) /
												complianceAssessment.max_score}
											size="size-10"
										>
											{requirementAssessment.documentation_score ?? '--'}
										</ProgressRing>
									</div>
								{:else if requirementAssessment.is_scored}
									<div class="flex flex-row items-center space-x-2 w-full">
										<span>{m.scoreResult()}</span>
										<ProgressRing
											strokeWidth="20px"
											meterStroke={displayScoreColor(
												requirementAssessment.score,
												complianceAssessment.max_score
											)}
											value={(requirementAssessment.score * 100) / complianceAssessment.max_score}
											size="size-10"
										>
											{requirementAssessment.score ?? '--'}
										</ProgressRing>
									</div>
								{/if}
								<Accordion
									value={accordionItems[requirementAssessment.id]}
									onValueChange={(e) => (accordionItems[requirementAssessment.id] = e.value)}
								>
									{#if shallow}
										{#if requirementAssessment.observation}
											<MarkdownRenderer
												content={requirementAssessment.observation}
												class="text-primary-500"
											/>
										{:else}
											<p class="text-gray-400 italic">{m.noObservation()}</p>
										{/if}
									{:else}
										<Accordion.Item value="observation">
											{#snippet control()}
												<p class="flex">{m.observation()}</p>
											{/snippet}
											{#snippet panel()}
												<TableMarkdownField
													bind:value={requirementAssessment.observation}
													onSave={async (newValue) => {
														await update(requirementAssessment, 'observation');
														requirementAssessment.observationBuffer = newValue;
													}}
												/>
											{/snippet}
										</Accordion.Item>
									{/if}
									{#if requirementAssessment.evidences.length === 0 && shallow}
										<p class="text-gray-400 italic">{m.noEvidences()}</p>
									{:else}
										<Accordion.Item value="evidence">
											{#snippet control()}
												<p class="flex items-center space-x-2">
													<span>{m.evidence()}</span>
													{#key addedEvidence}
														{#if requirementAssessment.evidences != null}
															<span class="badge preset-tonal-primary"
																>{requirementAssessment.evidences.length}</span
															>
														{/if}
													{/key}
												</p>
											{/snippet}
											{#snippet panel()}
												<div class="flex flex-row space-x-2 items-center">
													{#if !shallow}
														<button
															class="btn preset-filled-primary-500 self-start"
															onclick={() =>
																modalEvidenceCreateForm(requirementAssessment.evidenceCreateForm)}
															type="button"
															><i class="fa-solid fa-plus mr-2"></i>{m.addEvidence()}</button
														>
														<button
															class="btn preset-filled-secondary-500 self-start"
															type="button"
															onclick={() => modalUpdateForm(requirementAssessment)}
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
											{/snippet}
										</Accordion.Item>
									{/if}
								</Accordion>
							</div>
						</form>
					{/if}
				</div>
			{/if}
		{/each}
	</div>
</div>
