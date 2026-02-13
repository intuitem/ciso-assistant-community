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
	import { complianceResultColorMap, complianceResultTailwindColorMap } from '$lib/utils/constants';
	import { displayScoreColor, formatScoreValue } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { Accordion, ProgressRing } from '@skeletonlabs/skeleton-svelte';
	import { superForm, type SuperForm } from 'sveltekit-superforms';
	import type { ActionData, PageData } from './$types';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { invalidateAll } from '$app/navigation';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	const result_options = [
		{ id: 'not_assessed', label: m.notAssessed() },
		{ id: 'non_compliant', label: m.nonCompliant() },
		{ id: 'partially_compliant', label: m.partiallyCompliant() },
		{ id: 'compliant', label: m.compliant() },
		{ id: 'not_applicable', label: m.notApplicable() }
	];
	let requirementAssessments = $derived(data.requirement_assessments);
	let complianceAssessment = $derived(data.compliance_assessment);

	const requirementHashmap = Object.fromEntries(
		data.requirements.map((requirement: Record<string, any>) => [requirement.id, requirement])
	);

	// --- Assessable items only (for prev/next navigation) ---
	const assessableItems = $derived(requirementAssessments.filter((ra) => ra.assessable));
	let currentIndex = $state(0);
	const currentItem = $derived(assessableItems[currentIndex]);

	function goTo(index: number) {
		if (index >= 0 && index < assessableItems.length) {
			currentIndex = index;
			// Scroll to top of the requirement card
			const el = document.getElementById('current-requirement');
			if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
		}
	}

	// --- Progress ---
	const totalAssessable = $derived(assessableItems.length);
	const assessedCount = $derived(
		assessableItems.filter((ra) => ra.result !== 'not_assessed').length
	);
	const progressPercent = $derived(
		totalAssessable > 0 ? Math.round((assessedCount / totalAssessable) * 100) : 0
	);

	// --- Update logic (same as table-mode) ---
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
		await invalidateAll();
		if (requirementAssessment.updateForm && requirementAssessment.updateForm.data) {
			requirementAssessment.updateForm.data[field] = value;
		}
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
		}, 500);
	}

	// --- Modals ---
	const modalStore: ModalStore = getModalStore();

	function modalMeasureCreateForm(createform: SuperForm<any>): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: createform,
				formAction: '?/createAppliedControl',
				invalidateAll: true,
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
				formAction: '?/createEvidence',
				invalidateAll: true,
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

	// --- Score forms ---
	let scoreForms = $state({});
	let docScoreForms = $state({});
	let isScoredForms = $state({});

	run(() => {
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

	let accordionItems: Record<string, ['' | 'observation' | 'evidence']> = $state(
		// svelte-ignore state_referenced_locally
		requirementAssessments.reduce((acc, requirementAssessment) => {
			return {
				...acc,
				[requirementAssessment.id]: ['']
			};
		})
	);

	// --- Title helper ---
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

	// --- ToC items ---
	const tocSections = $derived(
		assessableItems.map((ra, index) => {
			const req = ra.requirement;
			const refId = req?.ref_id ?? '';
			const name = req?.name ?? '';
			let title = '';
			if (refId && name) {
				title = `${refId} - ${name}`;
			} else if (refId) {
				title = refId;
			} else if (name) {
				title = name;
			} else {
				title = `#${index + 1}`;
			}
			return {
				index,
				id: ra.id,
				title,
				result: ra.result
			};
		})
	);

	// ToC visibility
	let tocCollapsed = $state(false);

	// Keyboard navigation
	function handleKeydown(event: KeyboardEvent) {
		if (event.metaKey || event.ctrlKey) return;
		if (document.activeElement?.tagName !== 'BODY') return;
		if (event.key === 'ArrowRight' || event.key === 'n') {
			event.preventDefault();
			goTo(currentIndex + 1);
		}
		if (event.key === 'ArrowLeft' || event.key === 'p') {
			event.preventDefault();
			goTo(currentIndex - 1);
		}
	}

	import { onMount } from 'svelte';
	onMount(() => {
		document.addEventListener('keydown', handleKeydown);
		return () => document.removeEventListener('keydown', handleKeydown);
	});
</script>

<div class="flex flex-row h-full">
	<!-- ToC sidebar -->
	<div
		class="flex-shrink-0 transition-all duration-200 {tocCollapsed
			? 'w-10'
			: 'w-72'} sticky top-0 self-start max-h-screen overflow-y-auto border-r border-gray-200 bg-white"
	>
		<div class="flex items-center justify-between p-2 border-b border-gray-100">
			{#if !tocCollapsed}
				<span class="text-sm font-semibold text-gray-700">{m.tableOfContents()}</span>
			{/if}
			<button
				class="btn btn-sm preset-tonal-surface"
				onclick={() => (tocCollapsed = !tocCollapsed)}
			>
				<i class="fa-solid {tocCollapsed ? 'fa-angles-right' : 'fa-angles-left'} text-xs"></i>
			</button>
		</div>
		{#if !tocCollapsed}
			<nav class="p-2 space-y-0.5">
				{#each tocSections as section}
					<button
						class="w-full text-left px-2 py-1.5 text-xs rounded-md transition-colors truncate flex items-center gap-1.5
							{section.index === currentIndex
							? 'bg-primary-100 text-primary-800 font-semibold'
							: 'text-gray-600 hover:bg-gray-100'}"
						onclick={() => goTo(section.index)}
						title={section.title}
					>
						<span
							class="inline-block w-2 h-2 rounded-full flex-shrink-0"
							style="background-color: {complianceResultColorMap[section.result] ?? '#d1d5db'};"
						></span>
						<span class="truncate">{section.title}</span>
					</button>
				{/each}
			</nav>
		{/if}
	</div>

	<!-- Main content -->
	<div class="flex-1 flex flex-col space-y-4 p-4 min-w-0">
		<!-- Header: audit name + progress -->
		<div class="card bg-white shadow-sm px-5 py-3">
			<div class="flex items-center justify-between mb-2">
				<div class="flex items-center space-x-3">
					<a
						href="/auditee-dashboard"
						class="text-primary-600 hover:text-primary-800"
						title={m.auditDashboard()}
					>
						<i class="fa-solid fa-arrow-left"></i>
					</a>
					<div>
						<h2 class="text-lg font-semibold">{complianceAssessment.name}</h2>
						{#if complianceAssessment.framework?.name}
							<p class="text-sm text-gray-500">
								<i class="fa-solid fa-book mr-1"></i>{complianceAssessment.framework.name}
							</p>
						{/if}
					</div>
				</div>
				<div class="text-sm text-gray-500">
					{currentIndex + 1} / {totalAssessable}
				</div>
			</div>
			<!-- ETA / Due date -->
			{#if complianceAssessment.eta || complianceAssessment.due_date}
				<div class="flex items-center space-x-4 text-sm text-gray-500">
					{#if complianceAssessment.eta}
						<span
							><i class="fa-solid fa-calendar mr-1"></i>{m.eta()}: {complianceAssessment.eta}</span
						>
					{/if}
					{#if complianceAssessment.due_date}
						<span
							><i class="fa-solid fa-calendar-check mr-1"></i>{m.dueDate()}: {complianceAssessment.due_date}</span
						>
					{/if}
				</div>
			{/if}
			<!-- Progress bar -->
			<div class="flex items-center space-x-3">
				<div class="flex-1 bg-gray-200 rounded-full h-2">
					<div
						class="bg-indigo-500 h-2 rounded-full transition-all duration-300"
						style="width: {progressPercent}%"
					></div>
				</div>
				<span class="text-sm font-medium text-gray-600 whitespace-nowrap"
					>{assessedCount}/{totalAssessable} ({progressPercent}%)</span
				>
			</div>
		</div>

		<!-- Current requirement assessment -->
		{#if currentItem}
			{@const requirementAssessment = currentItem}
			{@const requirement =
				requirementHashmap[requirementAssessment.requirement] ?? requirementAssessment}
			<div
				id="current-requirement"
				class="card bg-white shadow-lg px-6 py-4 flex flex-col space-y-4"
			>
				<!-- Requirement title -->
				<div class="flex items-start justify-between">
					<div>
						<h3 class="text-xl font-semibold text-orange-600">
							{getTitle(requirementAssessment)}
						</h3>
						{#if requirement.ref_id && requirement.name}
							<p class="text-sm text-gray-500 mt-0.5">{requirement.ref_id}</p>
						{/if}
					</div>
					<span
						class="badge text-sm font-semibold px-2 py-1 rounded-md"
						style="background-color: {complianceResultColorMap[requirementAssessment.result] ??
							'#ddd'};"
					>
						{safeTranslate(requirementAssessment.result)}
					</span>
				</div>

				<!-- Description -->
				{#if requirementAssessment.requirement.description}
					<div class="card w-full font-light text-lg p-4 preset-tonal-primary">
						<h4 class="font-semibold text-base mb-1">
							<i class="fa-solid fa-file-lines mr-2"></i>{m.description()}
						</h4>
						<MarkdownRenderer content={requirementAssessment.requirement.description} />
					</div>
				{/if}

				<!-- Additional info (annotation, typical evidence) -->
				{#if requirementAssessment.requirement.annotation || requirementAssessment.requirement.typical_evidence}
					<div class="card p-4 preset-tonal-secondary text-sm flex flex-col space-y-2 w-full">
						<h4 class="font-semibold text-base">
							<i class="fa-solid fa-circle-info mr-2"></i>{m.additionalInformation()}
						</h4>
						{#if requirementAssessment.requirement.annotation}
							<div>
								<p class="font-medium"><i class="fa-solid fa-pencil mr-1"></i>{m.annotation()}</p>
								<MarkdownRenderer content={requirementAssessment.requirement.annotation} />
							</div>
						{/if}
						{#if requirementAssessment.requirement.typical_evidence}
							<div>
								<p class="font-medium">
									<i class="fa-solid fa-pencil mr-1"></i>{m.typicalEvidence()}
								</p>
								<MarkdownRenderer content={requirementAssessment.requirement.typical_evidence} />
							</div>
						{/if}
					</div>
				{/if}

				<!-- Assessment form -->
				{#if requirementAssessment.assessable}
					{#key requirementAssessment.id}
						<form
							class="flex flex-col space-y-4 items-center justify-evenly w-full"
							id="tableModeForm-{requirementAssessment.id}"
							action="?/updateRequirementAssessment"
							method="post"
						>
							<!-- Questions (if present) -->
							{#if requirementAssessment.requirement.questions != null && Object.keys(requirementAssessment.requirement.questions).length !== 0}
								<div class="flex flex-col w-full space-y-2">
									<Question
										questions={requirementAssessment.requirement.questions}
										initialValue={requirementAssessment.answers}
										field="answers"
										onChange={(urn, newAnswer) => {
											requirementAssessment.answers[urn] = newAnswer;
											update(requirementAssessment, 'answers', requirementAssessment.answers);
										}}
									/>
								</div>
							{/if}

							<!-- Result -->
							<div class="flex flex-col items-center w-full my-2">
								<p class="flex items-center font-semibold text-purple-600 italic">
									{m.result()}
								</p>
								{#if Object.values(requirementAssessment.requirement.questions || {}).some((question) => Array.isArray(question.choices) && question.choices.some((choice) => choice.compute_result !== undefined))}
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

							<!-- Score -->
							<div class="flex flex-col w-full place-items-center">
								{#if Object.values(requirementAssessment.requirement.questions || {}).some((question) => Array.isArray(question.choices) && question.choices.some((choice) => choice.add_score !== undefined))}
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
								{:else if requirementAssessment.result !== 'not_applicable'}
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
										disabled={!requirementAssessment.is_scored}
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
											disabled={!requirementAssessment.is_scored}
										/>
									{/if}
								{/if}
							</div>

							<Accordion
								value={accordionItems[requirementAssessment.id]}
								onValueChange={(e) => (accordionItems[requirementAssessment.id] = e.value)}
							>
								<!-- Applied Controls -->
								<Accordion.Item value="appliedControl">
									{#snippet control()}
										<p class="flex items-center space-x-2">
											<span>{m.appliedControl()}</span>
											{#if requirementAssessment.applied_controls != null}
												<span class="badge preset-tonal-primary"
													>{requirementAssessment.applied_controls.length}</span
												>
											{/if}
										</p>
									{/snippet}
									{#snippet panel()}
										<div class="flex flex-row space-x-2 items-center">
											<button
												class="btn preset-filled-primary-500 self-start"
												onclick={() =>
													modalMeasureCreateForm(requirementAssessment.measureCreateForm)}
												type="button"
											>
												<i class="fa-solid fa-plus mr-2"></i>{m.addAppliedControl()}
											</button>
											<button
												class="btn preset-filled-secondary-500 self-start"
												type="button"
												onclick={() =>
													modalUpdateForm(requirementAssessment, 'selectAppliedControls')}
											>
												<i class="fa-solid fa-hand-pointer mr-2"></i>{m.selectAppliedControls()}
											</button>
										</div>
										<div class="flex flex-wrap space-x-2 items-center">
											{#each requirementAssessment.applied_controls as ac}
												<p class="p-2">
													<Anchor class="anchor" href="/applied-controls/{ac.id}" label={ac.str}>
														<i class="fa-solid fa-fire-extinguisher mr-2"></i>{ac.str}
													</Anchor>
												</p>
											{/each}
										</div>
									{/snippet}
								</Accordion.Item>

								<!-- Evidence -->
								<Accordion.Item value="evidence">
									{#snippet control()}
										<p class="flex items-center space-x-2">
											<span>{m.evidence()}</span>
											{#if requirementAssessment.evidences != null}
												<span class="badge preset-tonal-primary" data-testid="evidence-count"
													>{requirementAssessment.evidences.length}</span
												>
											{/if}
										</p>
									{/snippet}
									{#snippet panel()}
										<div class="flex flex-row space-x-2 items-center">
											<button
												class="btn preset-filled-primary-500 self-start"
												onclick={() =>
													modalEvidenceCreateForm(requirementAssessment.evidenceCreateForm)}
												type="button"
												data-testid="create-evidence-button"
											>
												<i class="fa-solid fa-plus mr-2"></i>{m.addEvidence()}
											</button>
											<button
												class="btn preset-filled-secondary-500 self-start"
												type="button"
												data-testid="select-evidence-button"
												onclick={() => modalUpdateForm(requirementAssessment, 'selectEvidences')}
											>
												<i class="fa-solid fa-hand-pointer mr-2"></i>{m.selectEvidence()}
											</button>
										</div>
										<div class="flex flex-wrap space-x-2 items-center">
											{#each requirementAssessment.evidences as evidence}
												<p class="p-2">
													<Anchor
														class="anchor"
														href="/evidences/{evidence.id}"
														label={evidence.str}
														data-testid="evidence-link"
													>
														<i class="fa-solid fa-file-lines mr-2"></i>{evidence.str}
													</Anchor>
												</p>
											{/each}
										</div>
									{/snippet}
								</Accordion.Item>

								<!-- Observation -->
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
							</Accordion>
						</form>
					{/key}
				{/if}
			</div>

			<!-- Previous / Next navigation -->
			<div class="flex items-center justify-between card bg-white shadow-sm px-5 py-3">
				<button
					class="btn preset-tonal-surface"
					disabled={currentIndex === 0}
					onclick={() => goTo(currentIndex - 1)}
				>
					<i class="fa-solid fa-arrow-left mr-2"></i>
					{m.previous()}
				</button>
				<span class="text-sm text-gray-500">
					{currentIndex + 1} / {totalAssessable}
				</span>
				<button
					class="btn preset-filled-primary-500"
					disabled={currentIndex >= assessableItems.length - 1}
					onclick={() => goTo(currentIndex + 1)}
				>
					{m.next()}
					<i class="fa-solid fa-arrow-right ml-2"></i>
				</button>
			</div>
		{:else}
			<div class="card bg-white shadow-lg p-8 text-center">
				<i class="fa-solid fa-clipboard-check text-4xl text-gray-300 mb-4"></i>
				<p class="text-gray-500 text-lg">{m.noAuditAssignments()}</p>
			</div>
		{/if}
	</div>
</div>
