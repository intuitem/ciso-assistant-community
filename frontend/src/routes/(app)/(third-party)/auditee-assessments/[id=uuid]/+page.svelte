<script lang="ts">
	import { run } from 'svelte/legacy';

	import { applyAction, deserialize } from '$app/forms';
	import { getToastStore } from '$lib/components/Toast/stores';
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
	import {
		displayScoreColor,
		formatScoreValue,
		isFieldVisible,
		resolveFieldVisibility
	} from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import { Accordion, Progress } from '@skeletonlabs/skeleton-svelte';
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

	// Field visibility based on viewer role (respondent if assigned actor, auditor otherwise)
	const fw = $derived(complianceAssessment.framework);
	const viewerRole = $derived((data.viewerRole ?? 'respondent') as 'respondent' | 'auditor');
	const showResult = $derived(isFieldVisible(fw, complianceAssessment, 'result', viewerRole));
	const showScore = $derived(isFieldVisible(fw, complianceAssessment, 'score', viewerRole));
	const showObservation = $derived(
		isFieldVisible(fw, complianceAssessment, 'observation', viewerRole)
	);
	const showAppliedControls = $derived(
		isFieldVisible(fw, complianceAssessment, 'applied_controls', viewerRole)
	);
	const showEvidences = $derived(isFieldVisible(fw, complianceAssessment, 'evidences', viewerRole));

	// Single assignment — the URL param (params.id) IS the assignment ID
	let assignment = $derived(data.assignment);
	let assignmentStatus = $derived(assignment?.status ?? null);

	let isAuditor = $derived(viewerRole === 'auditor');

	function isFieldEditable(fieldName: string): boolean {
		if (complianceAssessment.is_locked || complianceAssessment.status === 'in_review') return false;
		const vis = resolveFieldVisibility(fw, complianceAssessment, fieldName);
		if (vis === 'hidden') return false;
		if (isAuditor) {
			// Auditor can edit auditor-owned fields
			return vis === 'auditor';
		} else {
			// Respondent can edit everyone-visible fields (when assignment status allows)
			if (
				assignmentStatus === 'draft' ||
				assignmentStatus === 'submitted' ||
				assignmentStatus === 'closed'
			)
				return false;
			return vis === 'everyone';
		}
	}

	const canEditResult = $derived(isFieldEditable('result'));
	const canEditScore = $derived(isFieldEditable('score'));
	const canEditObservation = $derived(isFieldEditable('observation'));
	const canEditAppliedControls = $derived(isFieldEditable('applied_controls'));
	const canEditEvidences = $derived(isFieldEditable('evidences'));
	const canEditAnswers = $derived(isFieldEditable('answers'));

	let canSubmit = $derived(
		!isAuditor && (assignmentStatus === 'in_progress' || assignmentStatus === 'changes_requested')
	);

	// Get latest observation from the most recent changes_requested event
	let reviewerObservation = $derived.by(() => {
		if (assignmentStatus !== 'changes_requested' || !assignment?.events?.length) return null;
		const event = assignment.events.find(
			(e: { event_type: string; event_notes: string | null }) =>
				e.event_type === 'changes_requested' && e.event_notes
		);
		return event?.event_notes ?? null;
	});

	// History modal state
	let showHistoryModal = $state(false);

	function openHistoryModal() {
		showHistoryModal = true;
	}

	function closeHistoryModal() {
		showHistoryModal = false;
	}

	// Format event actor name
	function formatEventActor(
		actor: { first_name: string; last_name: string; email: string } | null
	): string {
		if (!actor) return '—';
		const name = [actor.first_name, actor.last_name].filter(Boolean).join(' ');
		return name || actor.email;
	}

	const toastStore = getToastStore();

	let isSubmitting = $state(false);

	async function handleSubmitForReview() {
		if (!assignment || !canSubmit) return;

		const body = m.submitForReviewConfirm();

		const modal: ModalSettings = {
			type: 'confirm',
			title: m.submitForReview(),
			body,
			response: async (confirmed: boolean) => {
				if (!confirmed) return;
				isSubmitting = true;
				try {
					const response = await fetch(`?/submitAssignment`, {
						method: 'POST',
						body: new FormData()
					});
					const result = deserialize(await response.text());
					if (result.type === 'success' && result.data?.submitStatus === 200) {
						await applyAction(result);
						await invalidateAll();
						toastStore.trigger({
							message: m.statusUpdatedSuccessfully(),
							background: 'variant-filled-success',
							timeout: 3000
						});
					} else {
						toastStore.trigger({
							message: result.data?.submitBody?.error || m.submissionFailed(),
							background: 'variant-filled-error',
							timeout: 5000
						});
					}
				} catch (error) {
					console.error('Error submitting assignment:', error);
					toastStore.trigger({
						message: m.anErrorOccurred(),
						background: 'variant-filled-error',
						timeout: 3000
					});
				} finally {
					isSubmitting = false;
				}
			}
		};
		modalStore.trigger(modal);
	}

	const requirementHashmap = $derived(
		Object.fromEntries(
			data.requirements.map((requirement: Record<string, any>) => [requirement.id, requirement])
		)
	);

	// --- Navigation items: assessable items + splash screen nodes + section headers ---
	type NavItem =
		| { type: 'assessment'; data: (typeof requirementAssessments)[0] }
		| { type: 'splash'; data: Record<string, any> }
		| { type: 'section'; data: Record<string, any> };

	const assessmentNavItems: NavItem[] = $derived(
		requirementAssessments
			.filter((ra) => ra.assessable)
			.map((ra) => ({ type: 'assessment' as const, data: ra }))
	);

	const splashNavItems: NavItem[] = $derived(
		data.requirements
			.filter((r: Record<string, any>) => r.display_mode === 'splash')
			.map((r: Record<string, any>) => ({ type: 'splash' as const, data: r }))
	);

	const navItems: NavItem[] = $derived.by(() => {
		const sorted = [...assessmentNavItems, ...splashNavItems].sort((a, b) => {
			const orderA =
				a.type === 'assessment'
					? (requirementHashmap[a.data.requirement?.id]?.order_id ?? 0)
					: (a.data.order_id ?? 0);
			const orderB =
				b.type === 'assessment'
					? (requirementHashmap[b.data.requirement?.id]?.order_id ?? 0)
					: (b.data.order_id ?? 0);
			return orderA - orderB;
		});

		// Insert section headers before groups of items sharing the same parent
		const seenParents = new Set<string>();
		const items: NavItem[] = [];
		for (const item of sorted) {
			const parentUrn =
				item.type === 'assessment'
					? requirementHashmap[item.data.requirement?.id]?.parent_requirement
					: item.data.parent_requirement;
			if (parentUrn && !seenParents.has(parentUrn)) {
				seenParents.add(parentUrn);
				const parentNode = data.requirements.find(
					(r: Record<string, any>) => r.id === parentUrn || r.urn === parentUrn
				);
				if (parentNode && parentNode.display_mode !== 'splash' && !parentNode.assessable) {
					items.push({ type: 'section', data: parentNode });
				}
			}
			items.push(item);
		}
		return items;
	});

	const assessableItems = $derived(
		navItems.filter((item): item is NavItem & { type: 'assessment' } => item.type === 'assessment')
	);

	let currentIndex = $state(0);
	const currentNavItem = $derived(navItems[currentIndex]);
	const currentItem = $derived(currentNavItem?.type === 'assessment' ? currentNavItem.data : null);
	const currentSplashNode = $derived(
		currentNavItem?.type === 'splash' ? currentNavItem.data : null
	);
	const currentSectionNode = $derived(
		currentNavItem?.type === 'section' ? currentNavItem.data : null
	);

	function goTo(index: number) {
		if (index >= 0 && index < navItems.length) {
			currentIndex = index;
			const el = document.getElementById('current-requirement');
			if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
		}
	}

	// --- Progress (question-based when framework has questions, else result-based) ---
	const totalQuestions = $derived(
		assessableItems.reduce((sum, item) => sum + (item.data.visible_questions ?? 0), 0)
	);
	const answeredQuestions = $derived(
		assessableItems.reduce((sum, item) => sum + (item.data.answered_questions ?? 0), 0)
	);
	const useQuestionProgress = $derived(totalQuestions > 0);

	const totalAssessable = $derived(assessableItems.length);
	const assessedCount = $derived(
		assessableItems.filter((item) => item.data.result !== 'not_assessed').length
	);
	const progressPercent = $derived(
		useQuestionProgress
			? Math.round((answeredQuestions / totalQuestions) * 100)
			: totalAssessable > 0
				? Math.round((assessedCount / totalAssessable) * 100)
				: 0
	);
	let hasUnassessed = $derived(
		useQuestionProgress ? answeredQuestions < totalQuestions : assessedCount < totalAssessable
	);

	// Per-requirement question completion status for ToC dots
	function getQuestionStatus(item: { data: Record<string, any> }): string {
		const visible = item.data.visible_questions ?? 0;
		const answered = item.data.answered_questions ?? 0;
		if (visible === 0) return '#22c55e'; // no questions = complete (green)
		if (answered >= visible) return '#22c55e'; // all answered (green)
		if (answered > 0) return '#f59e0b'; // partial (amber)
		return '#d1d5db'; // empty (gray)
	}

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
		requirementAssessments.reduce(
			(acc, requirementAssessment) => {
				return {
					...acc,
					[requirementAssessment.id]: ['']
				};
			},
			{} as Record<string, ['' | 'observation' | 'evidence']>
		)
	);

	// --- Title helper ---
	const titleMap = new Map();
	function getTitle(requirementAssessment: Record<string, any>) {
		if (titleMap.has(requirementAssessment.id)) {
			return titleMap.get(requirementAssessment.id);
		}
		const requirement =
			requirementHashmap[
				requirementAssessment.requirement?.id ?? requirementAssessment.requirement
			] ?? requirementAssessment;
		const result = requirement.display_short ? requirement.display_short : (requirement.name ?? '');
		titleMap.set(requirementAssessment.id, result);
		return result;
	}

	// --- ToC items ---
	const tocSections = $derived(
		navItems.map((item, index) => {
			if (item.type === 'splash') {
				return {
					index,
					id: item.data.id,
					title: item.data.name || 'Splash',
					result: '__splash__'
				};
			}
			if (item.type === 'section') {
				return {
					index,
					id: item.data.id,
					title: item.data.name || 'Section',
					result: '__section__'
				};
			}
			const req = item.data.requirement;
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
				id: item.data.id,
				title,
				result: item.data.result,
				questionColor: getQuestionStatus(item)
			};
		})
	);

	// ToC visibility and filtering
	let tocCollapsed = $state(false);
	let tocFilterResult = $state<string | null>(null);
	const resultCounts = $derived(
		result_options.map((opt) => ({
			...opt,
			count: tocSections.filter((s) => s.result === opt.id).length
		}))
	);
	const filteredTocSections = $derived(
		tocFilterResult ? tocSections.filter((s) => s.result === tocFilterResult) : tocSections
	);

	// Keyboard navigation
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && showHistoryModal) {
			event.preventDefault();
			closeHistoryModal();
			return;
		}
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

	import { page } from '$app/state';
	import CommentsPanel from '$lib/components/CommentsPanel/CommentsPanel.svelte';
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
			<div class="px-2 py-2 flex flex-wrap gap-1 border-b border-gray-200">
				{#each resultCounts as opt}
					{#if opt.count > 0}
						<button
							class="px-2 py-1 text-[10px] rounded transition-colors flex items-center gap-1.5
								{tocFilterResult === opt.id
								? 'bg-gray-700 text-white font-semibold'
								: 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'}"
							onclick={() => (tocFilterResult = tocFilterResult === opt.id ? null : opt.id)}
							title={opt.label}
						>
							<span
								class="inline-block w-1.5 h-1.5 rounded-full"
								style="background-color: {complianceResultColorMap[opt.id] ?? '#d1d5db'};"
							></span>
							{opt.count}
						</button>
					{/if}
				{/each}
			</div>
			<nav class="p-2 space-y-0.5">
				{#each filteredTocSections as section}
					{#if section.result === '__section__'}
						<button
							class="w-full text-left px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-gray-400 mt-2 truncate
								{section.index === currentIndex ? 'text-primary-700' : ''}"
							onclick={() => goTo(section.index)}
							title={section.title}
						>
							<span class="truncate">{section.title}</span>
						</button>
					{:else}
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
								style="background-color: {section.result === '__splash__'
									? '#a855f7'
									: useQuestionProgress
										? section.questionColor
										: (complianceResultColorMap[section.result] ?? '#d1d5db')};"
							></span>
							<span class="truncate">{section.title}</span>
						</button>
					{/if}
				{/each}
			</nav>
		{/if}
	</div>

	<!-- Main content -->
	<div class="flex-1 flex flex-col space-y-4 p-4 min-w-0">
		<!-- Header: audit name + progress -->
		<div class="card bg-white shadow-sm px-5 py-4 border-t-[3px] border-t-primary-500">
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
					{currentIndex + 1} / {navItems.length}
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
						class="h-2 rounded-full transition-all duration-500 ease-out"
						style="width: {progressPercent}%; background: linear-gradient(90deg, var(--color-primary-500), var(--color-primary-400));"
					></div>
				</div>
				<span class="text-sm font-medium text-gray-600 whitespace-nowrap">
					{#if useQuestionProgress}
						{answeredQuestions}/{totalQuestions} {m.questions()} ({progressPercent}%)
					{:else}
						{assessedCount}/{totalAssessable} ({progressPercent}%)
					{/if}
				</span>
			</div>
		</div>

		<!-- Assignment status banners (respondent only) -->
		{#if isAuditor}
			<!-- Auditors see nothing here -->
		{:else if assignmentStatus === 'submitted'}
			<div
				class="bg-white border border-blue-200 border-l-[3px] border-l-blue-500 rounded-lg px-5 py-3 flex items-center gap-3 shadow-sm"
			>
				<div class="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center flex-shrink-0">
					<i class="fa-solid fa-clock text-blue-500 text-sm"></i>
				</div>
				<p class="text-sm text-blue-800 font-medium">{m.assignmentSubmittedBanner()}</p>
			</div>
		{:else if assignmentStatus === 'closed'}
			<div
				class="bg-white border border-green-200 border-l-[3px] border-l-emerald-500 rounded-lg px-5 py-3 flex items-center gap-3 shadow-sm"
			>
				<div
					class="w-8 h-8 rounded-full bg-green-50 flex items-center justify-center flex-shrink-0"
				>
					<i class="fa-solid fa-check-circle text-emerald-500 text-sm"></i>
				</div>
				<p class="text-sm text-green-800 font-medium">{m.assignmentClosedBanner()}</p>
			</div>
		{:else if assignmentStatus === 'changes_requested'}
			<div
				class="bg-white border border-red-200 border-l-[3px] border-l-red-500 rounded-lg px-5 py-3 flex flex-col gap-2 shadow-sm"
			>
				<div class="flex items-center gap-3">
					<div
						class="w-8 h-8 rounded-full bg-red-50 flex items-center justify-center flex-shrink-0"
					>
						<i class="fa-solid fa-rotate-left text-red-500 text-sm"></i>
					</div>
					<p class="text-sm text-red-800 font-medium">{m.assignmentChangesRequestedBanner()}</p>
				</div>
				{#if reviewerObservation}
					<div class="bg-red-50 rounded-md p-3 ml-11 text-sm text-red-700 whitespace-pre-line">
						<i class="fa-solid fa-comment-dots mr-1"></i>
						{reviewerObservation}
					</div>
				{/if}
				{#if assignment?.events?.length > 0}
					<button
						class="ml-11 badge bg-gray-100 text-gray-600 text-xs hover:bg-gray-200 cursor-pointer transition-colors"
						onclick={openHistoryModal}
						title={m.viewHistory()}
					>
						<i class="fa-solid fa-clock-rotate-left mr-1"></i>
						{m.eventsHistory()}
						<span class="badge bg-gray-100 text-gray-500 text-[10px] ml-1"
							>{assignment.events.length}</span
						>
					</button>
				{/if}
			</div>
		{:else if assignmentStatus === 'draft'}
			<div
				class="bg-white border border-gray-200 border-l-[3px] border-l-gray-400 rounded-lg px-5 py-3 flex items-center gap-3 shadow-sm"
			>
				<div
					class="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0"
				>
					<i class="fa-solid fa-hourglass text-gray-400 text-sm"></i>
				</div>
				<p class="text-sm text-gray-600 font-medium">{m.assignmentAwaitingStart()}</p>
			</div>
		{/if}

		<!-- Submit for Review button -->
		{#if canSubmit}
			<div class="flex flex-col items-end gap-2">
				<button
					class="btn preset-filled-primary-500"
					onclick={handleSubmitForReview}
					disabled={isSubmitting}
				>
					{#if isSubmitting}
						<i class="fa-solid fa-spinner fa-spin mr-2"></i>
					{:else}
						<i class="fa-solid fa-paper-plane mr-2"></i>
					{/if}
					{m.submitForReview()}
				</button>
			</div>
		{/if}

		<!-- Read-only banner (only for CA-level locks, not assignment-level) -->
		{#if complianceAssessment.is_locked || complianceAssessment.status === 'in_review'}
			<div
				class="bg-white border border-yellow-200 border-l-[3px] border-l-yellow-500 rounded-lg px-5 py-3 flex items-center gap-3 shadow-sm"
			>
				<div
					class="w-8 h-8 rounded-full bg-yellow-50 flex items-center justify-center flex-shrink-0"
				>
					<i class="fa-solid fa-lock text-yellow-500 text-sm"></i>
				</div>
				<p class="text-sm text-yellow-800 font-medium">
					{complianceAssessment.is_locked
						? m.lockedAssessmentMessage()
						: m.assessmentInReviewMessage()}
				</p>
			</div>
		{/if}

		<!-- Current item: splash screen or requirement assessment -->
		{#if currentSplashNode}
			<div
				id="current-requirement"
				class="card bg-white shadow-md border-l-4 border-l-purple-400 overflow-hidden"
			>
				{#if currentSplashNode.name}
					<div class="px-6 py-4 border-b border-purple-100 flex items-center gap-2">
						<i class="fa-solid fa-display text-purple-400"></i>
						<span class="text-lg font-semibold text-gray-800">{currentSplashNode.name}</span>
					</div>
				{/if}
				<div class="px-6 py-5">
					<MarkdownRenderer content={currentSplashNode.description} />
				</div>
			</div>
		{:else if currentSectionNode}
			<div
				id="current-requirement"
				class="card bg-gray-50 shadow-sm border-l-4 border-l-gray-400 px-6 py-3"
			>
				<h3 class="text-lg font-semibold text-gray-700">{currentSectionNode.name}</h3>
				{#if currentSectionNode.description}
					<div class="mt-2">
						<MarkdownRenderer content={currentSectionNode.description} />
					</div>
				{/if}
			</div>
		{:else if currentItem}
			{@const requirementAssessment = currentItem}
			{@const requirement =
				requirementHashmap[
					requirementAssessment.requirement?.id ?? requirementAssessment.requirement
				] ?? requirementAssessment}
			<div
				id="current-requirement"
				class="card bg-white shadow-md border-t-[3px] border-t-orange-400 px-6 py-5 flex flex-col space-y-4"
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
				</div>

				<!-- Description -->
				{#if requirement.description}
					<div class="card w-full font-light text-lg p-4 preset-tonal-primary">
						<h4 class="font-semibold text-base mb-1">
							<i class="fa-solid fa-file-lines mr-2"></i>{m.description()}
						</h4>
						<MarkdownRenderer content={requirement.description} />
					</div>
				{/if}

				<!-- Additional info (annotation, typical evidence) -->
				{#if requirement.annotation || requirement.typical_evidence}
					<div class="card p-4 preset-tonal-secondary text-sm flex flex-col space-y-2 w-full">
						<h4 class="font-semibold text-base">
							<i class="fa-solid fa-circle-info mr-2"></i>{m.additionalInformation()}
						</h4>
						{#if requirement.annotation}
							<div>
								<p class="font-medium"><i class="fa-solid fa-pencil mr-1"></i>{m.annotation()}</p>
								<MarkdownRenderer content={requirement.annotation} />
							</div>
						{/if}
						{#if requirement.typical_evidence}
							<div>
								<p class="font-medium">
									<i class="fa-solid fa-pencil mr-1"></i>{m.typicalEvidence()}
								</p>
								<MarkdownRenderer content={requirement.typical_evidence} />
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
							{#if requirement.questions != null && Object.keys(requirement.questions).length !== 0}
								<div class="flex flex-col w-full space-y-2">
									<Question
										questions={requirement.questions}
										initialValue={requirementAssessment.answers}
										field="answers"
										disabled={!canEditAnswers}
										onChange={(urn, newAnswer) => {
											requirementAssessment.answers[urn] = newAnswer;
											update(requirementAssessment, 'answers', requirementAssessment.answers);
										}}
									/>
								</div>
							{/if}

							<!-- Result -->
							{#if showResult || Object.values(requirement.questions || {}).some((question) => Array.isArray(question.choices) && question.choices.some((choice) => choice.compute_result !== undefined))}
								<div class="flex flex-col items-center w-full my-2">
									<p class="flex items-center font-semibold text-purple-600 italic">
										{m.result()}
									</p>
									{#if Object.values(requirement.questions || {}).some((question) => Array.isArray(question.choices) && question.choices.some((choice) => choice.compute_result !== undefined))}
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
											disabled={!canEditResult}
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
							{/if}

							<!-- Score -->
							{#if showScore}
								<div
									class="flex flex-col w-full place-items-center {!canEditScore
										? 'pointer-events-none opacity-60'
										: ''}"
								>
									{#if complianceAssessment.scoring_enabled && Object.values(requirement.questions || {}).some((question) => Array.isArray(question.choices) && question.choices.some((choice) => choice.add_score !== undefined))}
										<div class="flex flex-row items-center space-x-4">
											<span class="font-medium">{m.score()}</span>
											<div class="shrink-0 relative">
												<Progress
													value={formatScoreValue(
														requirementAssessment.score,
														complianceAssessment.max_score
													)}
													min={0}
													max={100}
												>
													<Progress.Circle class="[--size:--spacing(10)]">
														<Progress.CircleTrack />
														<Progress.CircleRange
															class={displayScoreColor(
																requirementAssessment.score,
																complianceAssessment.max_score
															)}
														/>
													</Progress.Circle>
													<div class="absolute inset-0 flex items-center justify-center">
														<span class="text-xs font-bold">{requirementAssessment.score}</span>
													</div>
												</Progress>
											</div>
										</div>
									{:else if complianceAssessment.scoring_enabled && requirementAssessment.result !== 'not_applicable'}
										<Score
											form={scoreForms[requirementAssessment.id]}
											min_score={complianceAssessment.min_score}
											max_score={complianceAssessment.max_score}
											scores_definition={complianceAssessment.scores_definition}
											field="score"
											label={complianceAssessment.show_documentation_score
												? m.implementationScore()
												: m.score()}
											styles="w-full p-1"
											onChange={(newScore) => {
												requirementAssessment.score = newScore;
												updateScore(requirementAssessment);
											}}
											disabled={!canEditScore || !requirementAssessment.is_scored}
										>
											{#snippet left()}
												<div>
													<Checkbox
														form={isScoredForms[requirementAssessment.id]}
														field="is_scored"
														disabled={!canEditScore}
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
												scores_definition={complianceAssessment.scores_definition}
												field="documentation_score"
												label={m.documentationScore()}
												isDoc={true}
												styles="w-full p-1"
												onChange={(newScore) => {
													requirementAssessment.documentation_score = newScore;
													updateScore(requirementAssessment);
												}}
												disabled={!canEditScore || !requirementAssessment.is_scored}
											/>
										{/if}
									{/if}
								</div>
							{/if}

							<Accordion
								value={accordionItems[requirementAssessment.id]}
								onValueChange={(e) => (accordionItems[requirementAssessment.id] = e.value)}
							>
								<!-- Applied Controls -->
								{#if showAppliedControls}
									<Accordion.Item value="appliedControl">
										<Accordion.ItemTrigger class="flex w-full items-center cursor-pointer">
											<p class="flex flex-1 items-center space-x-2 text-left">
												<span>{m.appliedControl()}</span>
												{#if requirementAssessment.applied_controls != null}
													<span class="badge preset-tonal-primary"
														>{requirementAssessment.applied_controls.length}</span
													>
												{/if}
											</p>

											<Accordion.ItemIndicator
												class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90"
												><svg
													xmlns="http://www.w3.org/2000/svg"
													width="14px"
													height="14px"
													viewBox="0 0 448 512"
													><path
														d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
													/></svg
												></Accordion.ItemIndicator
											>
										</Accordion.ItemTrigger>
										<Accordion.ItemContent>
											{#if canEditAppliedControls}
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
											{/if}
											<div class="flex flex-wrap space-x-2 items-center">
												{#each requirementAssessment.applied_controls ?? [] as ac}
													<p class="p-2">
														<Anchor class="anchor" href="/applied-controls/{ac.id}" label={ac.str}>
															<i class="fa-solid fa-fire-extinguisher mr-2"></i>{ac.str}
														</Anchor>
													</p>
												{/each}
											</div>
										</Accordion.ItemContent>
									</Accordion.Item>
								{/if}

								<!-- Evidence -->
								{#if showEvidences}
									<Accordion.Item value="evidence">
										<Accordion.ItemTrigger class="flex w-full items-center cursor-pointer">
											<p class="flex flex-1 items-center space-x-2 text-left">
												<span>{m.evidence()}</span>
												{#if requirementAssessment.evidences != null}
													<span class="badge preset-tonal-primary" data-testid="evidence-count"
														>{requirementAssessment.evidences.length}</span
													>
												{/if}
											</p>

											<Accordion.ItemIndicator
												class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90"
												><svg
													xmlns="http://www.w3.org/2000/svg"
													width="14px"
													height="14px"
													viewBox="0 0 448 512"
													><path
														d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
													/></svg
												></Accordion.ItemIndicator
											>
										</Accordion.ItemTrigger>
										<Accordion.ItemContent>
											{#if canEditEvidences}
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
														onclick={() =>
															modalUpdateForm(requirementAssessment, 'selectEvidences')}
													>
														<i class="fa-solid fa-hand-pointer mr-2"></i>{m.selectEvidence()}
													</button>
												</div>
											{/if}
											<div class="flex flex-wrap space-x-2 items-center">
												{#each requirementAssessment.evidences ?? [] as evidence}
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
										</Accordion.ItemContent>
									</Accordion.Item>
								{/if}

								<!-- Observation -->
								{#if showObservation}
									<Accordion.Item value="observation">
										<Accordion.ItemTrigger class="flex w-full items-center cursor-pointer">
											<p class="flex flex-1 text-left">{m.observation()}</p>

											<Accordion.ItemIndicator
												class="transition-transform duration-200 data-[state=open]:rotate-0 data-[state=closed]:-rotate-90"
												><svg
													xmlns="http://www.w3.org/2000/svg"
													width="14px"
													height="14px"
													viewBox="0 0 448 512"
													><path
														d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
													/></svg
												></Accordion.ItemIndicator
											>
										</Accordion.ItemTrigger>
										<Accordion.ItemContent>
											<TableMarkdownField
												bind:value={requirementAssessment.observation}
												disabled={!canEditObservation}
												onSave={async (newValue) => {
													await update(requirementAssessment, 'observation');
													requirementAssessment.observationBuffer = newValue;
												}}
											/>
										</Accordion.ItemContent>
									</Accordion.Item>
								{/if}
							</Accordion>
						</form>
					{/key}
				{/if}
				{#if page.data?.featureflags?.comments}
					<CommentsPanel parentType="requirement_assessment" parentId={requirementAssessment.id} />
				{/if}
			</div>
		{/if}

		<!-- Previous / Next navigation (shown for both splash and assessment items) -->
		{#if currentSplashNode || currentItem}
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
					{currentIndex + 1} / {navItems.length}
				</span>
				<button
					class="btn preset-filled-primary-500"
					disabled={currentIndex >= navItems.length - 1}
					onclick={() => goTo(currentIndex + 1)}
				>
					{m.next()}
					<i class="fa-solid fa-arrow-right ml-2"></i>
				</button>
			</div>
		{:else}
			<div class="flex flex-col items-center justify-center py-20">
				<div class="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mb-5">
					<i class="fa-solid fa-clipboard-check text-2xl text-gray-300"></i>
				</div>
				<p class="text-gray-400">{m.noAuditAssignments()}</p>
			</div>
		{/if}
	</div>
</div>

<!-- History Modal -->
{#if showHistoryModal && assignment?.events?.length > 0}
	<div class="fixed inset-0 bg-black/50 z-40" onclick={closeHistoryModal} role="presentation"></div>
	<div class="fixed inset-0 z-50 flex items-center justify-center p-4">
		<div
			class="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col"
			onclick={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			aria-labelledby="history-modal-title"
		>
			<!-- Header -->
			<div class="flex items-center justify-between p-4 border-b">
				<h2 id="history-modal-title" class="h4 font-semibold">
					<i class="fa-solid fa-clock-rotate-left text-primary-500 mr-2"></i>
					{m.eventsHistory()}
				</h2>
				<button
					class="btn btn-sm preset-ghost-surface"
					onclick={closeHistoryModal}
					aria-label={m.close()}
				>
					<i class="fa-solid fa-times"></i>
				</button>
			</div>

			<!-- Content -->
			<div class="p-4 overflow-y-auto flex-1">
				<div class="mb-3">
					<span class="text-sm text-gray-600">
						{complianceAssessment.name}
					</span>
				</div>

				<div class="space-y-3">
					{#each assignment.events as event}
						<div class="flex gap-3">
							<div class="flex flex-col items-center">
								<div
									class="w-2 h-2 rounded-full mt-1.5 flex-shrink-0 {event.event_type ===
									'changes_requested'
										? 'bg-red-400'
										: event.event_type === 'closed'
											? 'bg-emerald-500'
											: event.event_type === 'submitted'
												? 'bg-blue-400'
												: event.event_type === 'in_progress'
													? 'bg-amber-400'
													: 'bg-gray-300'}"
								></div>
								<div class="w-px flex-1 bg-gray-200 mt-1"></div>
							</div>
							<div class="pb-3 flex-1">
								<div class="flex items-center gap-2 text-sm">
									<span
										class="font-medium px-1.5 py-0.5 rounded text-xs {event.event_type ===
										'changes_requested'
											? 'bg-red-100 text-red-700'
											: event.event_type === 'closed'
												? 'bg-green-100 text-green-700'
												: event.event_type === 'submitted'
													? 'bg-blue-100 text-blue-700'
													: event.event_type === 'in_progress'
														? 'bg-orange-100 text-orange-700'
														: 'bg-gray-100 text-gray-700'}"
									>
										{safeTranslate(event.event_type)}
									</span>
									<span class="text-gray-500 text-xs">
										{formatEventActor(event.event_actor)}
									</span>
								</div>
								<span class="text-gray-400 text-xs">
									{new Date(event.created_at).toLocaleString()}
								</span>
								{#if event.event_notes}
									<div
										class="mt-1.5 text-sm text-gray-700 whitespace-pre-line bg-gray-50 border border-gray-100 rounded-md px-3 py-2"
									>
										{event.event_notes}
									</div>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</div>

			<!-- Footer -->
			<div class="p-4 border-t bg-gray-50 rounded-b-lg">
				<button class="btn preset-filled-surface-500 w-full" onclick={closeHistoryModal}>
					{m.close()}
				</button>
			</div>
		</div>
	</div>
{/if}
