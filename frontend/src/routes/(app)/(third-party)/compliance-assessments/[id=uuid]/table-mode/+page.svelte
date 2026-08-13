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
	import { complianceResultColorMap, complianceStatusColorMap } from '$lib/utils/constants';
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
	import type { Actions, PageData } from './$types';
	import { onMount, tick } from 'svelte';
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

	const requirementHashmap = Object.fromEntries(
		data.requirements.map((requirement: Record<string, any>) => [requirement.id, requirement])
	);

	// Initialize hide suggestion state
	let hideSuggestionHashmap: Record<string, boolean> = $state({});
	// Reactive copy of the loaded assessments; re-synced on data reload
	let requirementAssessments = $state(data.requirement_assessments);
	$effect(() => {
		requirementAssessments = data.requirement_assessments;
	});
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

	// Title with a leading ref_id stripped (only when a separator follows)
	function getDisplayTitle(requirementAssessment: Record<string, any>) {
		const title = getTitle(requirementAssessment) ?? '';
		const refId = getRefId(requirementAssessment);
		if (refId && title.startsWith(refId)) {
			const match = title.slice(refId.length).match(/^\s*[-–—:.)]*\s+(.*)$/s);
			if (match) return match[1].trim() || title;
		}
		return title;
	}

	// Detail chips share the per-requirement open-set
	function isSectionOpen(raId: string, key: string) {
		return (accordionItems[raId] ?? []).includes(key);
	}
	function toggleSection(raId: string, key: string) {
		const open = (accordionItems[raId] ?? []).filter(Boolean);
		accordionItems[raId] = open.includes(key) ? open.filter((k) => k !== key) : [...open, key];
	}

	// Patch one or more fields of a requirement assessment
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

	// Patch a single field; refresh only when the backend recomputes derived fields
	async function update(
		requirementAssessment: Record<string, any>,
		field: string,
		{ refresh = false }: { refresh?: boolean } = {}
	) {
		const value = requirementAssessment[field];
		await updateBulk(requirementAssessment, {
			[field]: value
		});

		if (refresh && invalidateAllBool) {
			await invalidateAll();
		}

		// Update requirementAssessment.updateForm.data with the specified field and value
		if (requirementAssessment.updateForm && requirementAssessment.updateForm.data) {
			requirementAssessment.updateForm.data[field] = value;
		}
	}

	// Auditor view toggle: assessment (answers read-only) vs questions-only
	let questionnaireMode = $state(questionnaireOnly);

	const modalStore: ModalStore = getModalStore();

	function modalMeasureCreateForm(requirementAssessment: Record<string, any>): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: requirementAssessment.measureCreateForm,
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

	function modalEvidenceCreateForm(requirementAssessment: Record<string, any>): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: requirementAssessment.evidenceCreateForm,
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

	// Header scores, refetched after a score edit
	let auditScores = $state(data.scores);
	$effect(() => {
		auditScores = data.scores;
	});
	async function refreshScores() {
		try {
			const res = await fetch(`/compliance-assessments/${complianceAssessment.id}/global-score`);
			if (res.ok) auditScores = await res.json();
		} catch {
			/* keep the last known scores on failure */
		}
	}

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
				await refreshScores();
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

	// Header toggle collapses/expands sections, not the item chips
	let allExpanded = $state(true);
	// Section tree from urn/parent_urn: ancestors, depth, per-heading counts
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
		if (row && !row.ancestors.every((id) => !collapsedSections[id])) return false;
		if (!tocFilterResult) return true;
		const ra = requirementAssessments[index];
		const isSplash = ra.display_mode === 'splash' || ra.requirement?.display_mode === 'splash';
		if (isSplash) return false;
		if (row?.isHeading) return filterSections.has(ra.id);
		return ra.result === tocFilterResult;
	}

	// Collapse/expand SECTIONS only, never the item chips
	function setAllExpanded(expanded: boolean) {
		const next: Record<string, boolean> = {};
		if (!expanded) {
			for (const row of sectionInfo.rows) if (row.isHeading) next[row.id] = true;
		}
		collapsedSections = next;
		allExpanded = expanded;
	}

	let showToc = $state(true);

	// AppBar height; the page header sticks below it
	let stickyTop = $state(0);
	// Header height (for the sticky TOC column)
	let headerHeight = $state(0);
	// Sticky section-bar height, for the scroll offset
	let stickySectionHeight = $state(0);
	// Whether the audit has any section headings (flat audits pin no sticky bar).
	const hasSections = $derived(sectionInfo.rows.some((r) => r.isHeading));
	// Space a scrolled-to element must clear (AppBar + header + section bar)
	const scrollOffset = $derived(
		stickyTop + headerHeight + (hasSections ? stickySectionHeight || 52 : 0) + 4
	);

	// Scroll-spy: section enclosing the topmost visible row (null when flat)
	let activeSectionId = $state<string | null>(null);
	const activeSection = $derived(
		activeSectionId ? requirementAssessments.find((ra) => ra.id === activeSectionId) : null
	);
	// Row id -> enclosing section id (self if heading, else nearest ancestor)
	const sectionByRow = $derived.by(() => {
		const map: Record<string, string | null> = {};
		requirementAssessments.forEach((ra, i) => {
			const row = sectionInfo.rows[i];
			map[ra.id] = !row ? null : row.isHeading ? ra.id : (row.ancestors[0] ?? null);
		});
		return map;
	});

	// --- Table of contents (left column, toggled from the header) ---
	let tocCollapsed = $state(false);
	let tocFilterResult = $state<string | null>(null);

	// Sections with a requirement matching the active result filter
	const filterSections = $derived.by(() => {
		const s = new Set<string>();
		if (!tocFilterResult) return s;
		requirementAssessments.forEach((ra, i) => {
			if (ra.assessable && ra.result === tocFilterResult) {
				for (const id of sectionInfo.rows[i]?.ancestors ?? []) s.add(id);
			}
		});
		return s;
	});

	const tocSections = $derived(
		requirementAssessments.map((ra, index) => {
			const row = sectionInfo.rows[index];
			const isSplash = ra.display_mode === 'splash' || ra.requirement?.display_mode === 'splash';
			return {
				id: ra.id,
				title: getDisplayTitle(ra) || getTitle(ra) || `#${index + 1}`,
				refId: getRefId(ra),
				result: isSplash ? '__splash__' : row?.isHeading ? '__section__' : ra.result,
				isSection: !!row?.isHeading,
				depth: row?.depth ?? 1,
				ancestors: row?.ancestors ?? []
			};
		})
	);
	const resultCounts = $derived(
		result_options.map((opt) => ({
			...opt,
			count: tocSections.filter((s) => s.result === opt.value).length
		}))
	);
	const filteredTocSections = $derived(
		tocFilterResult ? tocSections.filter((s) => s.result === tocFilterResult) : tocSections
	);

	// Compact score formatting for the header analytics.
	function fmtScore(v: number | null | undefined) {
		return v == null ? '--' : Math.round(Number(v) * 10) / 10;
	}

	// Audit progress analytics (assessable requirements only).
	const assessableTotal = $derived(
		tocSections.filter((s) => s.result !== '__section__' && s.result !== '__splash__').length
	);
	const assessedCount = $derived(
		tocSections.filter(
			(s) => s.result !== '__section__' && s.result !== '__splash__' && s.result !== 'not_assessed'
		).length
	);

	// Scroll to a requirement, expanding any collapsed parent section first.
	async function goToRequirement(item: { id: string; ancestors: string[] }) {
		for (const sectionId of item.ancestors) collapsedSections[sectionId] = false;
		await tick();
		document
			.getElementById(`requirement-${item.id}`)
			?.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}
	onMount(() => {
		// Show TOC only if there are more than 3 requirements
		showToc = requirementAssessments.length > 3;

		const cleanups: Array<() => void> = [];

		// Track the AppBar height
		const appbar = document.querySelector('.sticky.top-0.z-50') as HTMLElement | null;
		if (appbar) {
			const measure = () => (stickyTop = appbar.getBoundingClientRect().height);
			measure();
			const ro = new ResizeObserver(measure);
			ro.observe(appbar);
			window.addEventListener('resize', measure);
			cleanups.push(() => {
				ro.disconnect();
				window.removeEventListener('resize', measure);
			});
		}

		// Scroll-spy: current section = enclosing section of the topmost still-visible row.
		const updateActiveSection = () => {
			const offset = stickyTop + headerHeight + 4;
			let rowId: string | null = null;
			for (const el of document.querySelectorAll<HTMLElement>('[data-row-anchor]')) {
				if (el.getBoundingClientRect().bottom > offset) {
					rowId = el.getAttribute('data-ra-id');
					break;
				}
			}
			const section = rowId ? (sectionByRow[rowId] ?? null) : null;
			const headEl = section ? document.getElementById(`requirement-${section}`) : null;
			activeSectionId = headEl && headEl.getBoundingClientRect().top < offset ? section : null;
		};
		updateActiveSection();
		// Coalesce scroll bursts into at most one layout-reading pass per frame.
		let scrollRaf = 0;
		const onScroll = () => {
			if (scrollRaf) return;
			scrollRaf = requestAnimationFrame(() => {
				scrollRaf = 0;
				updateActiveSection();
			});
		};
		window.addEventListener('scroll', onScroll, { passive: true });
		cleanups.push(() => {
			window.removeEventListener('scroll', onScroll);
			if (scrollRaf) cancelAnimationFrame(scrollRaf);
		});

		return () => cleanups.forEach((fn) => fn());
	});
</script>

<!-- Compact toggle chip for a detail section (controls / evidences). -->
{#snippet chip(cfg: Record<string, any>)}
	<button
		type="button"
		data-testid={cfg.triggerTestId}
		onclick={() => toggleSection(cfg.raId, cfg.key)}
		class="inline-flex h-9 items-center gap-2 rounded-md border px-3 text-sm transition-colors {isSectionOpen(
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

<!-- Related-object panel (controls / evidences): create/select + item list -->
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
			<div class="flex flex-wrap gap-2">
				{#each cfg.items as item}
					<Anchor
						class="inline-flex items-center gap-2 rounded-md border border-surface-200 bg-surface-50 px-2.5 py-1 text-sm text-surface-800 transition-colors hover:border-primary-300 hover:bg-primary-50"
						href="{cfg.hrefBase}/{item.id}"
						label={item.str}
						data-testid={cfg.linkTestId}
					>
						<i class="fa-solid {cfg.itemIcon} text-surface-400"></i>
						<span class="truncate max-w-[18rem]">{item.str}</span>
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
			<div class="flex flex-row flex-wrap items-start gap-x-6 gap-y-2">
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
						disabled={isReadOnly}
						onChange={(v) => {
							ra.score = v;
							if (!ra.is_scored) {
								ra.is_scored = true;
								update(ra, 'is_scored');
							}
							updateScore(ra);
						}}
					/>
				</div>
				{#if complianceAssessment.show_documentation_score}
					<div class="flex flex-col gap-1">
						<span class="text-xs font-semibold text-surface-500 italic"
							>{m.documentationScore()}</span
						>
						<ScoreControl
							value={ra.documentation_score}
							min={raMin}
							max={raMax}
							scoresDefinition={raScoresDef}
							isDoc
							disabled={isReadOnly}
							onChange={(v) => {
								ra.documentation_score = v;
								if (!ra.is_scored) {
									ra.is_scored = true;
									update(ra, 'is_scored');
								}
								updateScore(ra);
							}}
						/>
					</div>
				{/if}
			</div>
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
	<div class="card px-6 py-4 bg-white flex flex-col shadow-lg w-full h-full space-y-3">
		{#if !questionnaireOnly}
			<div
				class="sticky z-20 -mx-6 flex flex-col gap-2 border-b border-surface-200 bg-white/80 px-6 py-2.5 backdrop-blur"
				style="top: {stickyTop}px"
				bind:clientHeight={headerHeight}
			>
				<!-- Row 1: navigation + global controls -->
				<div class="flex flex-row items-center justify-between gap-4">
					<a
						href="/compliance-assessments/{complianceAssessment.id}"
						class="flex items-center space-x-2 text-primary-800 hover:text-primary-600 min-w-0"
						data-testid="back-to-audit"
					>
						<i class="fa-solid fa-arrow-left"></i>
						<p class="truncate">{m.goBackToAudit()} {complianceAssessment.name}</p>
					</a>
					<div class="flex items-center gap-4 shrink-0">
						{#if !shallow}
							<div class="flex items-center gap-1">
								<Anchor
									href="/compliance-assessments/{complianceAssessment.id}/edit?next={page.url
										.pathname}"
									label={m.edit()}
									class="btn btn-sm preset-tonal-surface"
								>
									<i class="fa-solid fa-pen mr-2"></i>{m.edit()}
								</Anchor>
								<Anchor
									href="/compliance-assessments/{complianceAssessment.id}/action-plan"
									label={m.actionPlan()}
									class="btn btn-sm preset-tonal-surface"
								>
									<i class="fa-solid fa-list-check mr-2"></i>{m.actionPlan()}
								</Anchor>
								<Anchor
									href="/compliance-assessments/{complianceAssessment.id}/evidences-list"
									label={m.evidences()}
									class="btn btn-sm preset-tonal-surface"
								>
									<i class="fa-solid fa-file-lines mr-2"></i>{m.evidences()}
								</Anchor>
							</div>
							<button
								type="button"
								class="btn btn-sm preset-tonal-surface"
								onclick={() => setAllExpanded(!allExpanded)}
							>
								<i class="fa-solid {allExpanded ? 'fa-compress' : 'fa-expand'} mr-2"></i>
								{allExpanded ? m.collapseAll() : m.expandAll()}
							</button>
						{/if}
						{#if hasQuestions}
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

				<!-- Row 2: TOC toggle + audit progress analytics -->
				{#if (!shallow && showToc) || assessableTotal > 0}
					<div class="flex items-center gap-4 flex-wrap border-t border-surface-100 pt-2">
						{#if !shallow && showToc}
							<button
								type="button"
								class="btn btn-sm shrink-0 border font-medium preset-tonal-surface border-surface-300"
								onclick={() => (tocCollapsed = !tocCollapsed)}
								aria-pressed={!tocCollapsed}
							>
								<i class="fa-solid {tocCollapsed ? 'fa-list-ul' : 'fa-angles-left'} mr-2"></i>
								{m.tableOfContents()}
							</button>
						{/if}
						{#if assessableTotal > 0}
							<div class="flex flex-1 items-center gap-3 min-w-[200px]">
								<span class="text-xs font-medium text-surface-500 shrink-0">
									{m.progress()}: {assessedCount}/{assessableTotal}
								</span>
								<div
									class="flex flex-1 h-5 overflow-hidden rounded-sm border border-surface-200 bg-surface-100"
									role="img"
									aria-label="{m.progress()}: {assessedCount}/{assessableTotal}"
								>
									{#each resultCounts as opt}
										{#if opt.count > 0}
											{@const pct = (opt.count / assessableTotal) * 100}
											<div
												class="flex h-full items-center justify-center overflow-hidden"
												style="width: {pct}%; background-color: {complianceResultColorMap[
													opt.value
												] ?? '#d1d5db'}; color: {opt.value === 'not_applicable'
													? '#ffffff'
													: '#1f2937'}"
												title="{opt.label}: {opt.count} ({Math.round(pct)}%)"
											>
												{#if pct >= 9}
													<span class="text-[10px] font-semibold leading-none"
														>{Math.round(pct)}%</span
													>
												{/if}
											</div>
										{/if}
									{/each}
								</div>
							</div>
						{/if}
						{#if complianceAssessment.scoring_enabled}
							<div class="flex items-center gap-2 shrink-0 text-xs font-medium">
								<span
									class="inline-flex items-center gap-1 rounded-md bg-surface-100 px-2 py-1 text-surface-700"
								>
									{m.score()}:
									<span class="font-semibold">{fmtScore(auditScores?.implementation_score)}</span>
									{#if auditScores?.max_score}<span class="text-surface-400"
											>/{auditScores.max_score}</span
										>{/if}
								</span>
								{#if complianceAssessment.show_documentation_score}
									<span
										class="inline-flex items-center gap-1 rounded-md bg-surface-100 px-2 py-1 text-surface-700"
									>
										{m.documentationScore()}:
										<span class="font-semibold">{fmtScore(auditScores?.documentation_score)}</span>
										{#if auditScores?.max_score}<span class="text-surface-400"
												>/{auditScores.max_score}</span
											>{/if}
									</span>
								{/if}
							</div>
						{/if}
					</div>
				{/if}
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
		<div class="flex flex-row items-start gap-4">
			{#if !shallow && !questionnaireOnly && showToc && !tocCollapsed}
				<!-- Table of contents column (child of the card, toggled from the header) -->
				<nav
					class="hidden lg:block w-64 shrink-0 self-start sticky overflow-y-auto border-r border-surface-200 pr-2"
					style="top: {stickyTop + headerHeight}px; max-height: calc(100vh - {stickyTop +
						headerHeight}px - 1rem)"
				>
					{#if showResult}
						<div class="flex flex-wrap gap-1 pb-2 mb-1 border-b border-surface-200">
							{#each resultCounts as opt}
								{#if opt.count > 0}
									<button
										type="button"
										class="px-2 py-1 text-[10px] rounded transition-colors flex items-center gap-1.5 {tocFilterResult ===
										opt.value
											? 'bg-surface-700 text-white font-semibold'
											: 'bg-white text-surface-700 hover:bg-surface-100 border border-surface-200'}"
										onclick={() =>
											(tocFilterResult = tocFilterResult === opt.value ? null : opt.value)}
										title={opt.label}
									>
										<span
											class="inline-block w-1.5 h-1.5 rounded-full"
											style="background-color: {complianceResultColorMap[opt.value] ?? '#d1d5db'}"
										></span>
										{opt.count}
									</button>
								{/if}
							{/each}
						</div>
					{/if}
					<div class="space-y-0.5">
						{#each filteredTocSections as section}
							{#if section.isSection}
								<button
									type="button"
									class="w-full text-left py-1 text-[10px] font-bold uppercase tracking-wide text-surface-400 mt-2 truncate hover:text-primary-700"
									style="padding-left: {0.25 + (section.depth - 1) * 0.5}rem"
									onclick={() => goToRequirement(section)}
									title={section.title}
								>
									{section.refId ? `${section.refId} ` : ''}{section.title}
								</button>
							{:else}
								<button
									type="button"
									class="w-full text-left py-1.5 pr-2 text-xs rounded-md transition-colors truncate flex items-center gap-1.5 text-surface-600 hover:bg-surface-100"
									style="padding-left: {0.25 + (section.depth - 1) * 0.5}rem"
									onclick={() => goToRequirement(section)}
									title={section.title}
								>
									<span
										class="inline-block w-2 h-2 rounded-full flex-shrink-0"
										style="background-color: {section.result === '__splash__'
											? '#a855f7'
											: (complianceResultColorMap[section.result] ?? '#d1d5db')}"
									></span>
									<span class="truncate"
										>{section.refId ? `${section.refId} ` : ''}{section.title}</span
									>
								</button>
							{/if}
						{/each}
					</div>
				</nav>
			{/if}
			<div class="flex-1 min-w-0">
				{#if activeSection}
					<!-- Single sticky "current section" bar (updated on scroll) -->
					<div
						class="sticky z-10 pb-2"
						style="top: {stickyTop + headerHeight}px"
						bind:clientHeight={stickySectionHeight}
					>
						<button
							type="button"
							onclick={() => toggleSectionCollapse(activeSection.id)}
							class="flex w-full items-center gap-2 rounded-lg border border-orange-200 border-l-4 border-l-orange-400 bg-orange-50 px-3 py-2 text-left shadow-md"
						>
							<i
								class="fa-solid fa-chevron-down text-orange-500 text-xs transition-transform {collapsedSections[
									activeSection.id
								]
									? '-rotate-90'
									: ''}"
							></i>
							{#if getRefId(activeSection)}
								<span class="shrink-0 font-semibold text-sm text-orange-600"
									>{getRefId(activeSection)}</span
								>
							{/if}
							<span class="font-semibold text-orange-800 truncate"
								>{getDisplayTitle(activeSection)}</span
							>
						</button>
					</div>
				{/if}
				<ul data-testid="requirement-assessments" class="space-y-3">
					{#each requirementAssessments as requirementAssessment, i}
						{@const row = sectionInfo.rows[i]}
						{#if isRowVisible(i)}
							<li class="list-none">
								{#if requirementAssessment.display_mode === 'splash' || requirementAssessment.requirement?.display_mode === 'splash'}
									<!-- Splash screen node: full-width markdown block -->
									<div class="my-4" data-row-anchor data-ra-id={requirementAssessment.id}>
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
										data-row-anchor
										data-ra-id={requirementAssessment.id}
										style:scroll-margin-top="{scrollOffset}px"
									>
										<button
											type="button"
											onclick={() => toggleSectionCollapse(requirementAssessment.id)}
											aria-expanded={!collapsed}
											class="flex w-full items-center gap-2 rounded-lg border border-orange-200 border-l-4 border-l-orange-400 bg-orange-50 px-3 py-2 text-left transition-colors hover:bg-orange-100/70"
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
												class="font-semibold text-orange-800 {row.depth > 1
													? 'text-sm'
													: 'text-base'}">{getDisplayTitle(requirementAssessment)}</span
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
										data-row-anchor
										data-ra-id={requirementAssessment.id}
										style:scroll-margin-top="{scrollOffset}px"
									>
										<form
											id="tableModeForm-{requirementAssessment.id}"
											action="{actionPath}?/updateRequirementAssessment"
											method="post"
											class="flex flex-col gap-3 table-mode-form"
										>
											<!-- Row A: title -->
											<div class="flex items-center gap-3 flex-wrap">
												<div class="flex items-center gap-2 min-w-0">
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
												</div>

												{#if viewerRole === 'auditor' && showRespondentAlignment && requirementAssessment.respondent_alignment}
													<span class="flex flex-col items-end shrink-0 ml-auto">
														<span class="text-xs italic text-surface-500"
															>{m.respondentAnswered()}</span
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

											<!-- Description -->
											{#if requirementAssessment.requirement.description}
												<div class="text-sm text-surface-700" data-testid="description">
													<MarkdownRenderer
														content={requirementAssessment.requirement.description}
													/>
												</div>
											{/if}

											<!-- Row B: result / status / score -->
											{#if !questionnaireMode && (showResult || (!shallow && complianceAssessment.scoring_enabled))}
												<div class="flex flex-wrap items-start gap-x-6 gap-y-3">
													{#if !questionnaireMode && showResult}
														<div class="flex flex-col gap-1">
															<span class="text-xs font-semibold text-surface-500 italic"
																>{m.result()}</span
															>
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
																	colorMap={complianceResultColorMap}
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
														</div>
														{#if complianceAssessment.progress_status_enabled}
															<div class="flex flex-col gap-1">
																<span class="text-xs font-semibold text-surface-500 italic"
																	>{m.status()}</span
																>
																<SegmentedControl
																	options={status_options}
																	value={requirementAssessment.status}
																	colorMap={complianceStatusColorMap}
																	disabled={isReadOnly}
																	size="sm"
																	ariaLabel={m.status()}
																	onChange={(newValue) => {
																		const newStatus =
																			requirementAssessment.status === newValue
																				? 'to_do'
																				: newValue;
																		requirementAssessment.status = newStatus;
																		update(requirementAssessment, 'status');
																	}}
																/>
															</div>
														{/if}
													{/if}
													{@render scoreSlot(requirementAssessment)}
												</div>
											{/if}

											<!-- Additional information (annotation / typical evidence / mapping inference) -->
											{#if !questionnaireMode && (requirementAssessment.requirement.annotation || requirementAssessment.requirement.typical_evidence || requirementAssessment.mapping_inference?.result)}
												<div class="card p-3 preset-tonal-secondary text-sm cursor-auto w-full">
													<h2
														class="font-medium text-sm flex flex-row justify-between items-center"
													>
														<span>
															<i class="fa-solid fa-circle-info mr-2"
															></i>{m.additionalInformation()}
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
														disabled={isReadOnly || !questionnaireMode}
														shallow={shallow || !questionnaireMode}
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
														disabled={isReadOnly || !questionnaireMode}
														shallow={shallow || !questionnaireMode}
														onChange={(_urn, choiceUrn) => {
															const newAlignment = alignmentValueFromChoiceUrn(choiceUrn);
															requirementAssessment.respondent_alignment = newAlignment;
															update(requirementAssessment, 'respondent_alignment', {
																refresh: true
															});
														}}
													/>
												</div>
											{/if}
											{#if questionnaireMode && ((showResult && hasComputedResult(requirementAssessment.requirement.questions)) || (showScore && complianceAssessment.scoring_enabled && hasComputedScore(requirementAssessment.requirement.questions)))}
												<div
													class="mt-2 inline-flex w-fit flex-wrap items-center gap-x-8 gap-y-2 rounded-lg border border-surface-300 bg-surface-50 px-4 py-2.5 shadow-sm"
												>
													{#if showResult && hasComputedResult(requirementAssessment.requirement.questions)}
														<div class="flex flex-col gap-1">
															<span class="text-xs font-semibold text-surface-500 italic"
																>{m.result()}</span
															>
															<span
																class="badge text-sm font-semibold w-fit"
																style={resultBadgeStyle(requirementAssessment.result)}
															>
																{safeTranslate(requirementAssessment.result)}
															</span>
														</div>
													{/if}
													{#if showScore && complianceAssessment.scoring_enabled && hasComputedScore(requirementAssessment.requirement.questions)}
														{@const raMin =
															requirementAssessment.effective_min_score ??
															complianceAssessment.min_score}
														{@const raMax =
															requirementAssessment.effective_max_score ??
															complianceAssessment.max_score}
														{@const raScoresDef =
															requirementAssessment.effective_scores_definition ??
															data.scores.scores_definition}
														<div class="flex flex-col gap-1">
															<span class="text-xs font-semibold text-surface-500 italic"
																>{m.score()}</span
															>
															<ScoreControl
																editable={false}
																value={requirementAssessment.score}
																min={raMin}
																max={raMax}
																scoresDefinition={raScoresDef}
															/>
														</div>
													{/if}
												</div>
											{/if}
											{#if !questionnaireMode}
												<div class="flex flex-col gap-3">
													<!-- Related objects: controls / evidences -->
													{#if shallow}
														{#if showAppliedControls}
															{#if requirementAssessment.applied_controls.length === 0}
																<p class="text-surface-400 italic text-sm">
																	{m.noAppliedControlYet()}
																</p>
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
																<p
																	class="text-surface-400 italic text-sm"
																	data-testid="no-evidence"
																>
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
																onCreate: () => modalMeasureCreateForm(requirementAssessment),
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
																onCreate: () => modalEvidenceCreateForm(requirementAssessment),
																onSelect: () =>
																	modalUpdateForm(requirementAssessment, 'selectEvidences')
															})}
														{/if}
														{#if showObservation}
															<div class="flex flex-col gap-1.5">
																<span
																	class="text-xs font-semibold uppercase tracking-wide text-surface-500"
																	>{m.observation()}</span
																>
																<div class="card border border-surface-200 rounded-lg p-3">
																	<TableMarkdownField
																		value={requirementAssessment.observation}
																		disabled={isReadOnly}
																		onSave={async (newValue) => {
																			requirementAssessment.observation = newValue;
																			await update(requirementAssessment, 'observation');
																			requirementAssessment.observationBuffer = newValue;
																		}}
																	/>
																</div>
															</div>
														{/if}
													{/if}

													{#if shallow && showObservation}
														{#if requirementAssessment.observation}
															<MarkdownRenderer
																content={requirementAssessment.observation}
																class="text-primary-500"
															/>
														{:else}
															<p class="text-surface-400 italic text-sm">{m.noObservation()}</p>
														{/if}
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
	</div>
</div>
