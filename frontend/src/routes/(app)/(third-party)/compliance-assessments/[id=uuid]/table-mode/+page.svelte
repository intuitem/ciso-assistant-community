<script lang="ts">
	import { page } from '$app/state';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import Question from '$lib/components/Forms/Question.svelte';
	import RadioGroup from '$lib/components/Forms/RadioGroup.svelte';
	import Score from '$lib/components/Forms/Score.svelte';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import SplashCard from '$lib/components/FrameworkBuilder/SplashCard.svelte';
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
		complianceResultTailwindColorMap,
		complianceStatusTailwindColorMap
	} from '$lib/utils/constants';
	import {
		displayScoreColor,
		formatScoreValue,
		getFieldVisibility,
		hasComputedResult,
		hasComputedScore,
		shouldShowAutoQuestion,
		buildAutoAlignmentQuestion,
		alignmentValueFromChoiceUrn,
		choiceUrnFromAlignmentValue,
		alignmentColorMap,
		resultBadgeStyle,
		AUTO_ALIGNMENT_QUESTION_URN
	} from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { Progress, Switch } from '@skeletonlabs/skeleton-svelte';
	import { superForm, type SuperForm } from 'sveltekit-superforms';
	import type { Actions, PageData } from './$types';
	import TableOfContents from '$lib/components/TableOfContents/TableOfContents.svelte';
	import { type TocItem } from '$lib/utils/toc';
	import { onMount } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

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

	// Accordion section keys present on an assessable requirement card.
	const SECTION_VALUES = ['observation', 'appliedControl', 'evidence'];

	const requirementHashmap = Object.fromEntries(
		data.requirements.map((requirement: Record<string, any>) => [requirement.id, requirement])
	);

	// Initialize hide suggestion state
	let hideSuggestionHashmap: Record<string, boolean> = $state({});
	let requirementAssessments = $derived(data.requirement_assessments);
	let complianceAssessment = $derived(data.compliance_assessment);

	let isReadOnly = $derived(
		complianceAssessment.is_locked || complianceAssessment.status === 'in_review'
	);

	// Field visibility based on viewer role (server-computed from actor membership)
	const viewerRole: 'respondent' | 'auditor' = $derived(
		(data.viewerRole ?? 'auditor') as 'respondent' | 'auditor'
	);
	const fieldVis = $derived(getFieldVisibility(complianceAssessment, viewerRole));
	const showAnswers = $derived(fieldVis.showAnswers);
	const showResult = $derived(fieldVis.showResult);
	const showScore = $derived(fieldVis.showScore);
	const showObservation = $derived(fieldVis.showObservation);
	const showAppliedControls = $derived(fieldVis.showAppliedControls);
	const showEvidences = $derived(fieldVis.showEvidences);
	const showRespondentAlignment = $derived(fieldVis.showRespondentAlignment);

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

	// Reference id shown as a compact chip in front of an assessable requirement.
	function getRefId(requirementAssessment: Record<string, any>) {
		const requirement =
			requirementHashmap[requirementAssessment.requirement] ?? requirementAssessment;
		return requirement.ref_id ?? requirement.requirement?.ref_id ?? '';
	}

	// Title without the leading ref_id so it isn't shown twice next to the ref chip.
	// Only strips when a real separator (whitespace, dash, colon...) follows the ref_id.
	function getDisplayTitle(requirementAssessment: Record<string, any>) {
		const title = getTitle(requirementAssessment) ?? '';
		const refId = getRefId(requirementAssessment);
		if (refId && title.startsWith(refId)) {
			const match = title.slice(refId.length).match(/^\s*[-–—:.)]*\s+(.*)$/s);
			if (match) return match[1].trim() || title;
		}
		return title;
	}

	// Detail sections (observation / applied controls / evidences) are toggle chips
	// sharing the per-requirement open-set kept in accordionItems.
	function isSectionOpen(raId: string, key: string) {
		return (accordionItems[raId] ?? []).includes(key);
	}
	function toggleSection(raId: string, key: string) {
		const open = (accordionItems[raId] ?? []).filter(Boolean);
		accordionItems[raId] = open.includes(key) ? open.filter((k) => k !== key) : [...open, key];
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
	async function update(requirementAssessment: Record<string, any>, field: string) {
		const value = requirementAssessment[field];
		await updateBulk(requirementAssessment, {
			[field]: value
		});

		if (invalidateAllBool) {
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

	function modalMeasureCreateForm(createform: SuperForm<any>): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: createform,
				formAction: `${actionPath}?/createAppliedControl`,
				invalidateAll: invalidateAllBool,
				model: data.measureModel,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: safeTranslate('add-' + data.measureModel.localName)
		};
		modalStore.trigger(modal);
	}

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

	const requirementAssessmentScores = Object.fromEntries(
		// svelte-ignore state_referenced_locally
		requirementAssessments.map((requirement) => {
			return [requirement.id, [requirement.is_scored, requirement.score]];
		})
	);

	async function updateScore(requirementAssessment: Record<string, any>) {
		const score = requirementAssessment.score;
		const documentationScore = requirementAssessment.documentation_score;
		requirementAssessmentScores[requirementAssessment.id] = [
			requirementAssessment.is_scored,
			score,
			documentationScore
		];
		setTimeout(async () => {
			const currentScoreValue = requirementAssessmentScores[requirementAssessment.id];
			if (score === currentScoreValue[1] && documentationScore === currentScoreValue[2]) {
				await updateBulk(requirementAssessment, {
					score: score,
					documentation_score: documentationScore
				});
			}
		}, 500); // There must be 500ms without a score change for a request to be sent and modify the score of the RequirementAsessment in the backend
	}

	function modalUpdateForm(requirementAssessment: Record<string, any>, context: string): void {
		const modalComponent: ModalComponent = {
			ref: UpdateModal,
			props: {
				form: requirementAssessment.updateForm,
				model: requirementAssessment.updatedModel,
				object: requirementAssessment.object,
				formAction: '?/update&id=' + requirementAssessment.id,
				context
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

	// Create separate superForm instances for each requirement assessment
	let scoreForms = $state({});
	let docScoreForms = $state({});
	let isScoredForms = $state({});

	$effect(() => {
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

	const accordionItems: Record<string, string[]> = $state(
		// svelte-ignore state_referenced_locally
		requirementAssessments.reduce(
			(acc, requirementAssessment) => {
				acc[requirementAssessment.id] = [''];
				return acc;
			},
			{} as Record<string, string[]>
		)
	);

	let allExpanded = $state(false);
	function setAllAccordions(expanded: boolean) {
		for (const id of Object.keys(accordionItems)) {
			accordionItems[id] = expanded ? [...SECTION_VALUES] : [''];
		}
		allExpanded = expanded;
	}

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

{#snippet scoreRing(value: number | null, max: number, min: number)}
	<div class="shrink-0 relative">
		<Progress value={formatScoreValue(value, max, false, min)} min={0} max={100}>
			<Progress.Circle class="[--size:--spacing(10)]">
				<Progress.CircleTrack />
				<Progress.CircleRange class={displayScoreColor(value, max, false, min)} />
			</Progress.Circle>
			<div class="absolute inset-0 flex items-center justify-center">
				<span class="text-xs font-bold">{value ?? '--'}</span>
			</div>
		</Progress>
	</div>
{/snippet}

<!-- Compact toggle chip for a detail section (observation / controls / evidences). -->
{#snippet chip(cfg: Record<string, any>)}
	<button
		type="button"
		data-testid={cfg.triggerTestId}
		onclick={() => toggleSection(cfg.raId, cfg.key)}
		class="inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors {isSectionOpen(
			cfg.raId,
			cfg.key
		)
			? 'preset-tonal-primary border-primary-400'
			: 'border-surface-300 hover:preset-tonal-surface'}"
	>
		<i class="fa-solid {cfg.icon} text-surface-500"></i>
		<span class="font-medium">{cfg.label}</span>
		{#if cfg.count != null}
			<span class="badge preset-tonal-primary" data-testid={cfg.countTestId}>{cfg.count}</span>
		{/if}
		<i
			class="fa-solid fa-chevron-down text-xs text-surface-500 transition-transform {isSectionOpen(
				cfg.raId,
				cfg.key
			)
				? 'rotate-180'
				: ''}"
		></i>
	</button>
{/snippet}

<!--
	Panel body for a related-object section (applied controls, evidences).
	cfg carries the per-section labels, icons, items, test ids and modal callbacks.
-->
{#snippet detailPanel(cfg: Record<string, any>)}
	<div class="card border border-surface-200 rounded-lg p-3 space-y-2">
		{#if !shallow && !isReadOnly}
			<div class="flex flex-row gap-2 items-center">
				<button
					class="btn btn-sm preset-filled-primary-500"
					onclick={cfg.onCreate}
					type="button"
					data-testid={cfg.createTestId}
				>
					<i class="fa-solid fa-plus mr-2"></i>{cfg.createLabel}
				</button>
				<button
					class="btn btn-sm preset-filled-secondary-500"
					onclick={cfg.onSelect}
					type="button"
					data-testid={cfg.selectTestId}
				>
					<i class="fa-solid fa-hand-pointer mr-2"></i>{cfg.selectLabel}
				</button>
			</div>
		{/if}
		{#if cfg.items?.length}
			<div class="flex flex-wrap gap-x-4 gap-y-1 items-center">
				{#each cfg.items as item}
					<Anchor
						class="anchor"
						href="{cfg.hrefBase}/{item.id}"
						label={item.str}
						data-testid={cfg.linkTestId}
					>
						<i class="fa-solid {cfg.itemIcon} mr-2"></i>{item.str}
					</Anchor>
				{/each}
			</div>
		{:else}
			<p class="text-surface-400 italic text-sm">{cfg.emptyLabel}</p>
		{/if}
	</div>
{/snippet}

<div class="flex flex-col space-y-4 whitespace-pre-line">
	<TableOfContents
		items={tocItems}
		isVisible={showToc}
		position="right"
		className="hidden lg:block"
	/>
	<div class="card px-6 py-4 bg-white flex flex-col shadow-lg w-full h-full space-y-3">
		{#if !questionnaireOnly}
			<div
				class="sticky top-0 p-2 z-10 card bg-white items-center justify-between flex flex-row w-full gap-4"
			>
				<a
					href="/compliance-assessments/{complianceAssessment.id}"
					class="flex items-center space-x-2 text-primary-800 hover:text-primary-600"
					data-testid="back-to-audit"
				>
					<i class="fa-solid fa-arrow-left"></i>
					<p>{m.goBackToAudit()} {complianceAssessment.name}</p>
				</a>
				<div class="flex items-center gap-4">
					{#if !shallow}
						<button
							type="button"
							class="btn btn-sm preset-tonal-surface"
							onclick={() => setAllAccordions(!allExpanded)}
						>
							<i class="fa-solid {allExpanded ? 'fa-compress' : 'fa-expand'} mr-2"></i>
							{allExpanded ? m.collapseAll() : m.expandAll()}
						</button>
					{/if}
					{#if !hasQuestions}
						<div class="flex items-center justify-center space-x-4">
							{#if questionnaireMode}
								<p class="font-bold text-sm">{m.assessmentMode()}</p>
							{:else}
								<p class="font-bold text-sm text-green-500">{m.assessmentMode()}</p>
							{/if}
							<Switch
								name="questionnaireToggle"
								class="flex flex-row items-center justify-center"
								onCheckedChange={(e) => {
									questionnaireMode = e.checked;
								}}
							>
								<Switch.Control>
									<Switch.Thumb />
								</Switch.Control>
								<Switch.HiddenInput />
								{#if questionnaireMode}
									<p class="font-bold text-sm text-primary-500">{m.questionnaireMode()}</p>
								{:else}
									<p class="font-bold text-sm">{m.questionnaireMode()}</p>
								{/if}
							</Switch>
						</div>
					{/if}
				</div>
			</div>
		{/if}
		<!-- Read-only banner -->
		{#if isReadOnly}
			<div
				class="card bg-yellow-50 border border-yellow-300 px-5 py-3 flex items-center space-x-3 my-2"
			>
				<i class="fa-solid fa-lock text-yellow-600 text-lg"></i>
				<p class="text-yellow-800 font-medium">
					{complianceAssessment.is_locked
						? m.lockedAssessmentMessage()
						: m.assessmentInReviewMessage()}
				</p>
			</div>
		{/if}
		<ul data-testid="requirement-assessments" class="space-y-3">
			{#each requirementAssessments as requirementAssessment, i}
				<li class="list-none">
					{#if requirementAssessment.display_mode === 'splash' || requirementAssessment.requirement?.display_mode === 'splash'}
						<!-- Splash screen node: full-width markdown block -->
						<div class="my-4">
							<SplashCard
								name={requirementAssessment.name ?? requirementAssessment.requirement?.name}
								description={requirementAssessment.description ??
									requirementAssessment.requirement?.description}
								id="requirement-{requirementAssessment.id}"
							/>
						</div>
					{:else if !requirementAssessment.assessable}
						<!-- Section heading node: centered divider title (TOC anchor) -->
						<span
							class="relative flex justify-center py-4"
							id="requirement-{requirementAssessment.id}"
							data-toc
							data-toc-title={getTitle(requirementAssessment)}
							data-toc-level="0"
						>
							<div
								class="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-linear-to-r from-transparent via-gray-400 to-transparent opacity-75"
							></div>
							<span
								class="relative z-10 bg-white px-6 text-orange-600 font-semibold text-lg inline-flex items-center gap-3"
							>
								{getTitle(requirementAssessment)}
							</span>
						</span>
						{#if requirementAssessment.requirement.description}
							<div class="text-sm text-surface-600 text-center max-w-3xl mx-auto pb-2">
								<MarkdownRenderer content={requirementAssessment.requirement.description} />
							</div>
						{/if}
					{:else}
						<!-- Assessable requirement: compact card -->
						<div
							class="card border border-surface-200 rounded-xl p-4 space-y-3 shadow-sm"
							id="requirement-{requirementAssessment.id}"
							data-toc
							data-toc-title={getTitle(requirementAssessment)}
							data-toc-level="0"
						>
							<!-- Header: ref chip + title + weight + respondent answer -->
							<div class="flex items-start gap-3">
								{#if getRefId(requirementAssessment)}
									<span class="badge preset-tonal-secondary font-medium shrink-0 mt-0.5"
										>{getRefId(requirementAssessment)}</span
									>
								{/if}
								<div class="flex-1 min-w-0 flex items-center gap-2 flex-wrap">
									<span class="font-semibold text-base text-surface-900"
										>{getDisplayTitle(requirementAssessment)}</span
									>
									{#if typeof requirementAssessment.requirement?.weight === 'number' && Number.isFinite(requirementAssessment.requirement.weight) && requirementAssessment.requirement.weight !== 1}
										<span class="badge text-xs font-medium bg-indigo-100 text-indigo-800">
											{m.requirementWeight()}: {requirementAssessment.requirement.weight}
										</span>
									{/if}
								</div>
								{#if viewerRole === 'auditor' && showRespondentAlignment && requirementAssessment.respondent_alignment}
									<div class="flex flex-col items-end shrink-0">
										<p class="text-xs italic text-surface-500">{m.respondentAnswered()}</p>
										<span
											class="badge text-sm font-semibold text-white"
											style="background-color: {alignmentColorMap[
												requirementAssessment.respondent_alignment
											]}"
										>
											{safeTranslate(requirementAssessment.respondent_alignment)}
										</span>
									</div>
								{/if}
							</div>

							<!-- Description -->
							{#if requirementAssessment.requirement.description}
								<div class="text-sm text-surface-700" data-testid="description">
									<MarkdownRenderer content={requirementAssessment.requirement.description} />
								</div>
							{/if}

							<!-- Additional information (annotation / typical evidence / mapping inference) -->
							{#if requirementAssessment.requirement.annotation || requirementAssessment.requirement.typical_evidence || requirementAssessment.mapping_inference?.result}
								<div class="card p-3 preset-tonal-secondary text-sm cursor-auto w-full">
									<h2 class="font-medium text-sm flex flex-row justify-between items-center">
										<span>
											<i class="fa-solid fa-circle-info mr-2"></i>{m.additionalInformation()}
										</span>
										<button
											type="button"
											onclick={() => toggleSuggestion(requirementAssessment.id)}
										>
											{#if !hideSuggestionHashmap[requirementAssessment.id]}
												<i class="fa-solid fa-eye"></i>
											{:else}
												<i class="fa-solid fa-eye-slash"></i>
											{/if}
										</button>
									</h2>
									{#if !hideSuggestionHashmap[requirementAssessment.id]}
										{#if requirementAssessment.requirement.annotation}
											<div class="my-2">
												<p class="font-medium">
													<i class="fa-solid fa-pencil"></i>
													{m.annotation()}
												</p>
												<div class="py-1">
													<MarkdownRenderer
														content={requirementAssessment.requirement.annotation}
													/>
												</div>
											</div>
										{/if}
										{#if requirementAssessment.requirement.typical_evidence}
											<div class="my-2">
												<p class="font-medium">
													<i class="fa-solid fa-pencil"></i>
													{m.typicalEvidence()}
												</p>
												<div class="py-1">
													<MarkdownRenderer
														content={requirementAssessment.requirement.typical_evidence}
													/>
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
																{requirementAssessment.mapping_inference
																	.source_requirement_assessment.str}
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
																class="badge h-fit"
																style={resultBadgeStyle(
																	requirementAssessment.mapping_inference.result
																)}
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
								class="flex flex-col space-y-3 w-full table-mode-form"
								id="tableModeForm-{requirementAssessment.id}"
								action="{actionPath}?/updateRequirementAssessment"
								method="post"
							>
								<!-- Assessment band: result + status (always visible / editable) -->
								{#if !questionnaireMode && showResult}
									<div class="flex flex-row flex-wrap w-full gap-x-8 gap-y-3 items-start">
										<div class="flex flex-col gap-1">
											<p class="font-semibold text-sm text-purple-600 italic">{m.result()}</p>
											{#if hasComputedResult(requirementAssessment.requirement.questions)}
												<span
													class="badge text-sm font-semibold w-fit"
													style={resultBadgeStyle(requirementAssessment.result)}
												>
													{safeTranslate(requirementAssessment.result)}
												</span>
											{:else}
												<RadioGroup
													possibleOptions={result_options}
													key="id"
													labelKey="label"
													field="result"
													size="sm"
													colorMap={complianceResultTailwindColorMap}
													disabled={isReadOnly}
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
										{#if complianceAssessment.progress_status_enabled}
											<div class="flex flex-col gap-1">
												<p class="font-semibold text-sm text-blue-600 italic">{m.status()}</p>
												<RadioGroup
													possibleOptions={status_options}
													key="id"
													labelKey="label"
													field="status"
													size="sm"
													colorMap={complianceStatusTailwindColorMap}
													disabled={isReadOnly}
													initialValue={requirementAssessment.status}
													onChange={(newValue) => {
														const newStatus =
															requirementAssessment.status === newValue ? 'to_do' : newValue;
														requirementAssessment.status = newStatus;
														update(requirementAssessment, 'status');
													}}
												/>
											</div>
										{/if}
									</div>
								{/if}
								{#if showAnswers && requirementAssessment.requirement.questions != null && Object.keys(requirementAssessment.requirement.questions).length !== 0}
									<div class="flex flex-col w-full space-y-2">
										<Question
											questions={requirementAssessment.requirement.questions}
											initialValue={requirementAssessment.answers}
											field="answers"
											disabled={isReadOnly}
											{shallow}
											onChange={async (urn, newAnswer) => {
												requirementAssessment.answers[urn] = newAnswer;
												await updateBulk(requirementAssessment, {
													answers: { [urn]: newAnswer }
												});
												if (invalidateAllBool) {
													await invalidateAll();
												}
											}}
										/>
									</div>
								{/if}
								<!-- Auto-alignment question (when no framework questions) -->
								{#if shouldShowAutoQuestion(requirementAssessment.requirement, viewerRole, complianceAssessment)}
									<div class="flex flex-col w-full space-y-2">
										<Question
											questions={buildAutoAlignmentQuestion({
												text: m.areYouAlignedWithThisRequirement(),
												yes: m.yes(),
												no: m.no(),
												inProgress: m.inProgress(),
												notApplicable: m.notApplicable()
											})}
											initialValue={{
												[AUTO_ALIGNMENT_QUESTION_URN]: choiceUrnFromAlignmentValue(
													requirementAssessment.respondent_alignment
												)
											}}
											field="respondent_alignment"
											disabled={isReadOnly}
											onChange={(_urn, choiceUrn) => {
												const newAlignment = alignmentValueFromChoiceUrn(choiceUrn);
												requirementAssessment.respondent_alignment = newAlignment;
												update(requirementAssessment, 'respondent_alignment');
											}}
										/>
									</div>
								{/if}
								<div
									class="flex flex-col w-full {isReadOnly ? 'pointer-events-none opacity-60' : ''}"
								>
									{#if showScore && !shallow && complianceAssessment.scoring_enabled}
										{@const raMin =
											requirementAssessment.effective_min_score ?? complianceAssessment.min_score}
										{@const raMax =
											requirementAssessment.effective_max_score ?? complianceAssessment.max_score}
										{@const raScoresDef =
											requirementAssessment.effective_scores_definition ??
											data.scores.scores_definition}
										{#if hasComputedScore(requirementAssessment.requirement.questions)}
											<div class="flex flex-row items-center space-x-4">
												<span class="font-medium">{m.score()}</span>
												{@render scoreRing(requirementAssessment.score, raMax, raMin)}
											</div>
										{:else if requirementAssessment.result !== 'not_applicable'}
											<Score
												form={scoreForms[requirementAssessment.id]}
												min_score={raMin}
												max_score={raMax}
												scores_definition={raScoresDef}
												field="score"
												label={complianceAssessment.show_documentation_score
													? m.implementationScore()
													: m.score()}
												styles="w-full p-1"
												onChange={(newScore) => {
													requirementAssessment.score = newScore;
													updateScore(requirementAssessment);
												}}
												disabled={!requirementAssessment.is_scored}
											>
												{#snippet left()}
													<div>
														<Checkbox
															form={isScoredForms[requirementAssessment.id]}
															field="is_scored"
															disabled={isReadOnly}
															label={''}
															helpText={m.scoringHelpText()}
															checkboxComponent="switch"
															classes="h-full flex flex-row items-center justify-center my-1"
															classesContainer="h-full flex flex-row items-center space-x-4"
															onChange={async (newValue) => {
																requirementAssessment.is_scored = newValue;
																await update(requirementAssessment, 'is_scored');
															}}
														/>
													</div>
												{/snippet}
											</Score>
											{#if complianceAssessment.show_documentation_score}
												<Score
													form={docScoreForms[requirementAssessment.id]}
													min_score={raMin}
													max_score={raMax}
													scores_definition={raScoresDef}
													field="documentation_score"
													label={m.documentationScore()}
													isDoc={true}
													styles="w-full p-1"
													onChange={(newScore) => {
														requirementAssessment.documentation_score = newScore;
														updateScore(requirementAssessment);
													}}
													disabled={!requirementAssessment.is_scored}
												/>
											{/if}
										{/if}
									{:else if complianceAssessment.scoring_enabled && complianceAssessment.show_documentation_score && requirementAssessment.is_scored}
										{@const raMin =
											requirementAssessment.effective_min_score ?? complianceAssessment.min_score}
										{@const raMax =
											requirementAssessment.effective_max_score ?? complianceAssessment.max_score}
										<div class="flex flex-row items-center space-x-2 w-full">
											<span>{m.implementationScoreResult()}</span>
											{@render scoreRing(requirementAssessment.score, raMax, raMin)}
											<span>{m.documentationScoreResult()}</span>
											{@render scoreRing(requirementAssessment.documentation_score, raMax, raMin)}
										</div>
									{:else if complianceAssessment.scoring_enabled && requirementAssessment.is_scored}
										{@const raMin =
											requirementAssessment.effective_min_score ?? complianceAssessment.min_score}
										{@const raMax =
											requirementAssessment.effective_max_score ?? complianceAssessment.max_score}
										<div class="flex flex-row items-center space-x-2 w-full">
											<span>{m.scoreResult()}</span>
											{@render scoreRing(requirementAssessment.score, raMax, raMin)}
										</div>
									{/if}

									<!-- Detail sections: compact toggle chips + inline panels -->
									{#if shallow}
										{#if showObservation}
											{#if requirementAssessment.observation}
												<MarkdownRenderer
													content={requirementAssessment.observation}
													class="text-primary-500"
												/>
											{:else}
												<p class="text-surface-400 italic">{m.noObservation()}</p>
											{/if}
										{/if}
										{#if showAppliedControls}
											{#if requirementAssessment.applied_controls.length === 0}
												<p class="text-surface-400 italic">{m.noAppliedControlYet()}</p>
											{:else}
												<div class="flex flex-wrap gap-x-4 gap-y-1 items-center">
													{#each requirementAssessment.applied_controls as item}
														<Anchor
															class="anchor"
															href="/applied-controls/{item.id}"
															label={item.str}
														>
															<i class="fa-solid fa-fire-extinguisher mr-2"></i>{item.str}
														</Anchor>
													{/each}
												</div>
											{/if}
										{/if}
										{#if showEvidences}
											{#if requirementAssessment.evidences.length === 0}
												<p class="text-surface-400 italic" data-testid="no-evidence">
													{m.noEvidences()}
												</p>
											{:else}
												<div class="flex flex-wrap gap-x-4 gap-y-1 items-center">
													{#each requirementAssessment.evidences as item}
														<Anchor
															class="anchor"
															href="/evidences/{item.id}"
															label={item.str}
															data-testid="evidence-link"
														>
															<i class="fa-solid fa-file-lines mr-2"></i>{item.str}
														</Anchor>
													{/each}
												</div>
											{/if}
										{/if}
									{:else}
										<div class="flex flex-col gap-2 pt-1">
											<div class="flex flex-wrap gap-2 items-center">
												{#if showObservation}
													{@render chip({
														raId: requirementAssessment.id,
														key: 'observation',
														icon: 'fa-comment-dots',
														label: m.observation()
													})}
												{/if}
												{#if showAppliedControls}
													{@render chip({
														raId: requirementAssessment.id,
														key: 'appliedControl',
														icon: 'fa-fire-extinguisher',
														label: m.appliedControl(),
														count: requirementAssessment.applied_controls.length
													})}
												{/if}
												{#if showEvidences}
													{@render chip({
														raId: requirementAssessment.id,
														key: 'evidence',
														icon: 'fa-file-lines',
														label: m.evidence(),
														count: requirementAssessment.evidences.length,
														countTestId: 'evidence-count',
														triggerTestId: 'evidence-accordion-trigger'
													})}
												{/if}
											</div>

											{#if showObservation && isSectionOpen(requirementAssessment.id, 'observation')}
												<div class="card border border-surface-200 rounded-lg p-3">
													<TableMarkdownField
														bind:value={requirementAssessment.observation}
														disabled={isReadOnly}
														onSave={async (newValue) => {
															await update(requirementAssessment, 'observation');
															requirementAssessment.observationBuffer = newValue;
														}}
													/>
												</div>
											{/if}

											{#if showAppliedControls && isSectionOpen(requirementAssessment.id, 'appliedControl')}
												{@render detailPanel({
													items: requirementAssessment.applied_controls,
													hrefBase: '/applied-controls',
													itemIcon: 'fa-fire-extinguisher',
													emptyLabel: m.noAppliedControlYet(),
													createLabel: m.addAppliedControl(),
													selectLabel: m.selectAppliedControls(),
													onCreate: () =>
														modalMeasureCreateForm(requirementAssessment.measureCreateForm),
													onSelect: () =>
														modalUpdateForm(requirementAssessment, 'selectAppliedControls')
												})}
											{/if}

											{#if showEvidences && isSectionOpen(requirementAssessment.id, 'evidence')}
												{@render detailPanel({
													items: requirementAssessment.evidences,
													hrefBase: '/evidences',
													itemIcon: 'fa-file-lines',
													emptyLabel: m.noEvidences(),
													createLabel: m.addEvidence(),
													selectLabel: m.selectEvidence(),
													createTestId: 'create-evidence-button',
													selectTestId: 'select-evidence-button',
													linkTestId: 'evidence-link',
													onCreate: () =>
														modalEvidenceCreateForm(requirementAssessment.evidenceCreateForm),
													onSelect: () => modalUpdateForm(requirementAssessment, 'selectEvidences')
												})}
											{/if}
										</div>
									{/if}
								</div>
							</form>
						</div>
					{/if}
				</li>
			{/each}
		</ul>
	</div>
</div>
