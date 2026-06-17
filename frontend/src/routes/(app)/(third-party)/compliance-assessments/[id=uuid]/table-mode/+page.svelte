<script lang="ts">
	import { page } from '$app/state';
	import Question from '$lib/components/Forms/Question.svelte';
	import SegmentedControl from '$lib/components/Forms/SegmentedControl.svelte';
	import ScoreControl from '$lib/components/Forms/ScoreControl.svelte';
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
	import { Switch } from '@skeletonlabs/skeleton-svelte';
	import { type SuperForm } from 'sveltekit-superforms';
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
		{ value: 'not_assessed', label: m.notAssessed() },
		{ value: 'non_compliant', label: m.nonCompliant() },
		{ value: 'partially_compliant', label: m.partiallyCompliant() },
		{ value: 'compliant', label: m.compliant() },
		{ value: 'not_applicable', label: m.notApplicable() }
	];
	const status_options = [
		{ value: 'to_do', label: m.toDo() },
		{ value: 'in_progress', label: m.inProgress() },
		{ value: 'in_review', label: m.inReview() },
		{ value: 'done', label: m.done() }
	];

	// Detail chip keys present in the body of an assessable requirement card.
	const SECTION_VALUES = ['appliedControl', 'evidence'];

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

	// Underlying requirement node (carries urn / parent_urn / ref_id ...).
	function getNode(ra: Record<string, any>) {
		return ra?.requirement && typeof ra.requirement === 'object' ? ra.requirement : ra;
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

	// Open-set of detail chips (applied controls / evidences) per requirement.
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

	// Per-requirement fold state for the card body. The header (result / status /
	// score) stays visible and editable even while the body is collapsed.
	let expandedRA: Record<string, boolean> = $state(
		// svelte-ignore state_referenced_locally
		// Bodies start expanded so reading needs no click; collapsing is the opt-in densifier.
		requirementAssessments.reduce(
			(acc, ra) => {
				acc[ra.id] = true;
				return acc;
			},
			{} as Record<string, boolean>
		)
	);
	let allExpanded = $state(true);
	function toggleRA(id: string) {
		expandedRA[id] = !expandedRA[id];
	}
	// Section structure derived from the real tree (urn / parent_urn), not ref_id:
	// per-row ancestor headings, nesting depth, and assessable count under each heading.
	const sectionInfo = $derived.by(() => {
		// urn -> parent_urn for the whole framework tree.
		const parentByUrn: Record<string, string | null> = {};
		for (const item of data.requirements ?? []) {
			const n = getNode(item);
			if (n?.urn) parentByUrn[n.urn] = n.parent_urn ?? null;
		}
		// urn of each row + urn -> row id for heading rows (the collapsible ones).
		const urnByIndex = requirementAssessments.map((ra) => getNode(ra)?.urn ?? null);
		const headingIdByUrn: Record<string, string> = {};
		requirementAssessments.forEach((ra, idx) => {
			const urn = urnByIndex[idx];
			if (!urn) return;
			if (!(urn in parentByUrn)) parentByUrn[urn] = getNode(ra)?.parent_urn ?? null;
			const isSplash = ra.display_mode === 'splash' || ra.requirement?.display_mode === 'splash';
			if (!ra.assessable && !isSplash) headingIdByUrn[urn] = ra.id;
		});

		const counts: Record<string, number> = {};
		const rows = requirementAssessments.map((ra, idx) => {
			const isSplash = ra.display_mode === 'splash' || ra.requirement?.display_mode === 'splash';
			const ancestors: string[] = [];
			let parent = urnByIndex[idx] ? parentByUrn[urnByIndex[idx] as string] : null;
			let guard = 0;
			while (parent && guard++ < 100) {
				if (headingIdByUrn[parent]) ancestors.push(headingIdByUrn[parent]);
				parent = parentByUrn[parent] ?? null;
			}
			if (ra.assessable) for (const id of ancestors) counts[id] = (counts[id] ?? 0) + 1;
			return {
				id: ra.id,
				depth: ancestors.length + 1,
				isHeading: !ra.assessable && !isSplash,
				ancestors
			};
		});
		return { rows, counts };
	});

	// Collapsed sections hide every row nested under them (sections start expanded).
	let collapsedSections: Record<string, boolean> = $state({});
	function toggleSectionCollapse(id: string) {
		collapsedSections[id] = !collapsedSections[id];
	}
	function isRowVisible(index: number) {
		const row = sectionInfo.rows[index];
		return !row || row.ancestors.every((id) => !collapsedSections[id]);
	}

	function setAllExpanded(expanded: boolean) {
		for (const ra of requirementAssessments) {
			expandedRA[ra.id] = expanded;
		}
		// Expanding clears all section collapses; collapsing folds every section.
		const next: Record<string, boolean> = {};
		if (!expanded) {
			for (const row of sectionInfo.rows) if (row.isHeading) next[row.id] = true;
		}
		collapsedSections = next;
		allExpanded = expanded;
	}

	let tocItems: TocItem[] = $state([]);
	let showToc = $state(true);

	// Offset (px) so the page header sticks just below the app's sticky AppBar,
	// whose height is dynamic (title, breadcrumbs, sidebar state).
	let stickyTop = $state(0);
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

		// Track the app AppBar height so our header sticks right below it.
		const appbar = document.querySelector('.sticky.top-0.z-50') as HTMLElement | null;
		if (!appbar) return;
		const measure = () => (stickyTop = appbar.getBoundingClientRect().height);
		measure();
		const ro = new ResizeObserver(measure);
		ro.observe(appbar);
		window.addEventListener('resize', measure);
		return () => {
			ro.disconnect();
			window.removeEventListener('resize', measure);
		};
	});
</script>

<!-- Compact toggle chip for a detail section (controls / evidences). -->
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

<!-- Score slot rendered in the header (kept editable while the body is collapsed). -->
{#snippet scoreSlot(ra: Record<string, any>)}
	{#if showScore && !shallow && complianceAssessment.scoring_enabled}
		{@const raMin = ra.effective_min_score ?? complianceAssessment.min_score}
		{@const raMax = ra.effective_max_score ?? complianceAssessment.max_score}
		{@const raScoresDef = ra.effective_scores_definition ?? data.scores.scores_definition}
		{#if hasComputedScore(ra.requirement.questions)}
			<div class="flex flex-col gap-1">
				<span class="text-xs font-semibold text-surface-500 italic">{m.score()}</span>
				<ScoreControl
					editable={false}
					value={ra.score}
					min={raMin}
					max={raMax}
					scoresDefinition={raScoresDef}
				/>
			</div>
		{:else if ra.result !== 'not_applicable'}
			<div class="flex flex-col gap-1">
				<span class="text-xs font-semibold text-surface-500 italic"
					>{complianceAssessment.show_documentation_score
						? m.implementationScore()
						: m.score()}</span
				>
				<ScoreControl
					value={ra.score}
					min={raMin}
					max={raMax}
					scoresDefinition={raScoresDef}
					scored={ra.is_scored}
					disabled={isReadOnly}
					onScoredChange={async (v) => {
						ra.is_scored = v;
						await update(ra, 'is_scored');
					}}
					onChange={(v) => {
						ra.score = v;
						updateScore(ra);
					}}
				/>
			</div>
			{#if complianceAssessment.show_documentation_score}
				<div class="flex flex-col gap-1">
					<span class="text-xs font-semibold text-surface-500 italic">{m.documentationScore()}</span
					>
					<ScoreControl
						value={ra.documentation_score}
						min={raMin}
						max={raMax}
						scoresDefinition={raScoresDef}
						isDoc
						scored={ra.is_scored}
						disabled={isReadOnly}
						onChange={(v) => {
							ra.documentation_score = v;
							updateScore(ra);
						}}
					/>
				</div>
			{/if}
		{/if}
	{:else if complianceAssessment.scoring_enabled && complianceAssessment.show_documentation_score && ra.is_scored}
		{@const raMin = ra.effective_min_score ?? complianceAssessment.min_score}
		{@const raMax = ra.effective_max_score ?? complianceAssessment.max_score}
		<div class="flex items-center gap-4 flex-wrap">
			<ScoreControl
				editable={false}
				value={ra.score}
				min={raMin}
				max={raMax}
				label={m.implementationScoreResult()}
			/>
			<ScoreControl
				editable={false}
				value={ra.documentation_score}
				min={raMin}
				max={raMax}
				label={m.documentationScoreResult()}
			/>
		</div>
	{:else if complianceAssessment.scoring_enabled && ra.is_scored}
		{@const raMin = ra.effective_min_score ?? complianceAssessment.min_score}
		{@const raMax = ra.effective_max_score ?? complianceAssessment.max_score}
		<div class="flex flex-col gap-1">
			<span class="text-xs font-semibold text-surface-500 italic">{m.scoreResult()}</span>
			<ScoreControl editable={false} value={ra.score} min={raMin} max={raMax} />
		</div>
	{/if}
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
				class="sticky z-20 p-2 card bg-white items-center justify-between flex flex-row w-full gap-4"
				style="top: {stickyTop}px"
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
							onclick={() => setAllExpanded(!allExpanded)}
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
				{@const row = sectionInfo.rows[i]}
				{#if isRowVisible(i)}
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
							<!-- Section heading node: collapsible section bar (TOC anchor) -->
							{@const collapsed = !!collapsedSections[requirementAssessment.id]}
							{@const sectionCount = sectionInfo.counts[requirementAssessment.id] ?? 0}
							<div
								id="requirement-{requirementAssessment.id}"
								data-toc
								data-toc-title={getTitle(requirementAssessment)}
								data-toc-level="0"
								class="mt-2"
								style="margin-left: {(row.depth - 1) * 0.75}rem"
							>
								<button
									type="button"
									onclick={() => toggleSectionCollapse(requirementAssessment.id)}
									aria-expanded={!collapsed}
									class="flex w-full items-center gap-2 rounded-lg border border-orange-200 border-l-4 border-l-orange-400 bg-orange-50/60 px-3 py-2 text-left transition-colors hover:bg-orange-100/70"
								>
									<i
										class="fa-solid fa-chevron-down text-orange-500 text-xs transition-transform {collapsed
											? '-rotate-90'
											: ''}"
									></i>
									{#if getRefId(requirementAssessment)}
										<span class="shrink-0 font-semibold text-sm text-orange-600"
											>{getRefId(requirementAssessment)}</span
										>
									{/if}
									<span
										class="font-semibold text-orange-800 {row.depth > 1 ? 'text-sm' : 'text-base'}"
										>{getDisplayTitle(requirementAssessment)}</span
									>
									{#if sectionCount > 0}
										<span
											class="badge preset-tonal-secondary text-xs ml-auto shrink-0"
											title={m.requirements()}
										>
											{sectionCount}
										</span>
									{/if}
								</button>
								{#if requirementAssessment.requirement.description && !collapsed}
									<div class="text-sm text-surface-600 px-3 pt-1.5">
										<MarkdownRenderer content={requirementAssessment.requirement.description} />
									</div>
								{/if}
							</div>
						{:else}
							<!-- Assessable requirement: compact card -->
							<div
								class="card border border-surface-200 rounded-xl p-4 space-y-3 shadow-sm"
								id="requirement-{requirementAssessment.id}"
								data-toc
								data-toc-title={getTitle(requirementAssessment)}
								data-toc-level="0"
							>
								<form
									id="tableModeForm-{requirementAssessment.id}"
									action="{actionPath}?/updateRequirementAssessment"
									method="post"
									class="flex flex-col gap-3 table-mode-form"
								>
									<!-- Row A: foldable title -->
									<div class="flex items-center gap-3 flex-wrap">
										<button
											type="button"
											class="flex items-center gap-2 text-left min-w-0"
											onclick={() => toggleRA(requirementAssessment.id)}
											aria-expanded={!!expandedRA[requirementAssessment.id]}
										>
											{#if !shallow}
												<i
													class="fa-solid fa-chevron-right text-surface-400 text-sm transition-transform {expandedRA[
														requirementAssessment.id
													]
														? 'rotate-90'
														: ''}"
												></i>
											{/if}
											{#if getRefId(requirementAssessment)}
												<span class="badge preset-tonal-secondary font-medium shrink-0"
													>{getRefId(requirementAssessment)}</span
												>
											{/if}
											<span class="min-w-0 font-semibold text-base text-surface-900">
												{getDisplayTitle(requirementAssessment)}
											</span>
											{#if typeof requirementAssessment.requirement?.weight === 'number' && Number.isFinite(requirementAssessment.requirement.weight) && requirementAssessment.requirement.weight !== 1}
												<span
													class="badge text-xs font-medium bg-indigo-100 text-indigo-800 shrink-0"
												>
													{m.requirementWeight()}: {requirementAssessment.requirement.weight}
												</span>
											{/if}
										</button>

										{#if viewerRole === 'auditor' && showRespondentAlignment && requirementAssessment.respondent_alignment}
											<span class="flex flex-col items-end shrink-0 ml-auto">
												<span class="text-xs italic text-surface-500">{m.respondentAnswered()}</span
												>
												<span
													class="badge text-sm font-semibold text-white"
													style="background-color: {alignmentColorMap[
														requirementAssessment.respondent_alignment
													]}"
												>
													{safeTranslate(requirementAssessment.respondent_alignment)}
												</span>
											</span>
										{/if}
									</div>

									<!-- Row B: result / status / score, aligned under the name (editable while collapsed) -->
									{#if (!questionnaireMode && showResult) || (!shallow && complianceAssessment.scoring_enabled)}
										<div class="flex flex-wrap items-center gap-x-6 gap-y-3 pl-7">
											{#if !questionnaireMode && showResult}
												{#if hasComputedResult(requirementAssessment.requirement.questions)}
													<span
														class="badge text-sm font-semibold w-fit"
														style={resultBadgeStyle(requirementAssessment.result)}
													>
														{safeTranslate(requirementAssessment.result)}
													</span>
												{:else}
													<SegmentedControl
														options={result_options}
														value={requirementAssessment.result}
														colorMap={complianceResultTailwindColorMap}
														disabled={isReadOnly}
														size="sm"
														ariaLabel={m.result()}
														onChange={(newValue) => {
															const newResult =
																requirementAssessment.result === newValue
																	? 'not_assessed'
																	: newValue;
															requirementAssessment.result = newResult;
															update(requirementAssessment, 'result');
														}}
													/>
												{/if}
												{#if complianceAssessment.progress_status_enabled}
													<SegmentedControl
														options={status_options}
														value={requirementAssessment.status}
														colorMap={complianceStatusTailwindColorMap}
														disabled={isReadOnly}
														size="sm"
														ariaLabel={m.status()}
														onChange={(newValue) => {
															const newStatus =
																requirementAssessment.status === newValue ? 'to_do' : newValue;
															requirementAssessment.status = newStatus;
															update(requirementAssessment, 'status');
														}}
													/>
												{/if}
											{/if}
											{@render scoreSlot(requirementAssessment)}
										</div>
									{/if}

									<!-- Description: always visible, even when the body is collapsed -->
									{#if requirementAssessment.requirement.description}
										<div class="text-sm text-surface-700" data-testid="description">
											<MarkdownRenderer content={requirementAssessment.requirement.description} />
										</div>
									{/if}

									{#if shallow || expandedRA[requirementAssessment.id]}
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
																			{safeTranslate(
																				requirementAssessment.mapping_inference.result
																			)}
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

										<!-- Questions / auto-alignment -->
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
										<div class="flex flex-col gap-3">
											<!-- Related objects: controls / evidences -->
											{#if shallow}
												{#if showAppliedControls}
													{#if requirementAssessment.applied_controls.length === 0}
														<p class="text-surface-400 italic text-sm">{m.noAppliedControlYet()}</p>
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
														<p class="text-surface-400 italic text-sm" data-testid="no-evidence">
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
												<div class="flex flex-wrap gap-2 items-center">
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
														onSelect: () =>
															modalUpdateForm(requirementAssessment, 'selectEvidences')
													})}
												{/if}
											{/if}

											<!-- Observation: always at the end of the unfolded body -->
											{#if showObservation}
												<div class="space-y-1">
													<p class="text-sm font-medium text-surface-600">
														<i class="fa-solid fa-comment-dots mr-1 text-surface-500"
														></i>{m.observation()}
													</p>
													{#if shallow}
														{#if requirementAssessment.observation}
															<MarkdownRenderer
																content={requirementAssessment.observation}
																class="text-primary-500"
															/>
														{:else}
															<p class="text-surface-400 italic text-sm">{m.noObservation()}</p>
														{/if}
													{:else}
														<TableMarkdownField
															bind:value={requirementAssessment.observation}
															disabled={isReadOnly}
															onSave={async (newValue) => {
																await update(requirementAssessment, 'observation');
																requirementAssessment.observationBuffer = newValue;
															}}
														/>
													{/if}
												</div>
											{/if}
										</div>
									{/if}
								</form>
							</div>
						{/if}
					</li>
				{/if}
			{/each}
		</ul>
	</div>
</div>
