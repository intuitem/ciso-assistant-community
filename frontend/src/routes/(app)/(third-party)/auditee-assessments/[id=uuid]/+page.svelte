<script lang="ts">
	import { run } from 'svelte/legacy';

	import { applyAction, deserialize } from '$app/forms';
	import { getToastStore } from '#lib/components/Toast/stores.js';
	import Question from '#lib/components/Forms/Question.svelte';
	import RadioGroup from '#lib/components/Forms/RadioGroup.svelte';
	import Score from '#lib/components/Forms/Score.svelte';
	import MarkdownRenderer from '#lib/components/MarkdownRenderer.svelte';
	import SplashCard from '#lib/components/FrameworkBuilder/SplashCard.svelte';
	import TableMarkdownField from '#lib/components/Forms/TableMarkdownField.svelte';
	import CreateModal from '#lib/components/Modals/CreateModal.svelte';
	import SubmitAssignmentModal from '#lib/components/Modals/SubmitAssignmentModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '#lib/components/Modals/stores.js';
	import UpdateModal from '#lib/components/Modals/UpdateModal.svelte';
	import {
		complianceResultColorMap,
		complianceResultTailwindColorMap
	} from '#lib/utils/constants.js';
	import {
		displayScoreColor,
		formatScoreValue,
		getFieldVisibility,
		hasComputedResult,
		hasComputedScore,
		resultBadgeStyle,
		isFieldEditable as isFieldEditableHelper,
		shouldShowAutoQuestion,
		buildAutoAlignmentQuestion,
		alignmentValueFromChoiceUrn,
		choiceUrnFromAlignmentValue,
		alignmentColorMap,
		requirementResultOptions,
		AUTO_ALIGNMENT_QUESTION_URN
	} from '#lib/utils/helpers.js';
	import { safeTranslate } from '#lib/utils/i18n.js';
	import { m } from '#paraglide/messages.js';
	import ScorePair from '#lib/components/ComplianceAssessment/ScorePair.svelte';
	import { getLocale } from '#paraglide/runtime.js';
	import { formatDate } from '#lib/utils/datetime.js';
	import { Accordion, Popover, Progress } from '@skeletonlabs/skeleton-svelte';
	import { superForm, type SuperForm } from 'sveltekit-superforms';
	import type { ActionData, PageData } from './$types';
	import Anchor from '#lib/components/Anchor/Anchor.svelte';
	import { afterNavigate, refreshAll } from '$app/navigation';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	// Full list, used for the ToC result counts; the input radio filters per-row.
	const result_options = requirementResultOptions();

	const status_options = [
		{ id: 'to_do', label: m.toDo() },
		{ id: 'in_progress', label: m.inProgress() },
		{ id: 'in_review', label: m.inReview() },
		{ id: 'done', label: m.done() }
	];

	const extended_result_options = [
		{ id: 'major_nonconformity', label: m.majorNonconformity() },
		{ id: 'minor_nonconformity', label: m.minorNonconformity() },
		{ id: 'observation_sensitive_point', label: m.observationSensitivePoint() },
		{ id: 'opportunity_for_improvement', label: m.opportunityForImprovement() },
		{ id: 'good_practice', label: m.goodPractice() }
	];
	let requirementAssessments = $derived(data.requirement_assessments);
	let complianceAssessment = $derived(data.compliance_assessment);

	// Field visibility based on viewer role (respondent if assigned actor, auditor otherwise)
	const fw = $derived(complianceAssessment.framework);
	const viewerRole = $derived((data.viewerRole ?? 'respondent') as 'respondent' | 'auditor');
	const fieldVis = $derived(getFieldVisibility(complianceAssessment, viewerRole));
	const showAnswers = $derived(fieldVis.showAnswers);
	const showResult = $derived(fieldVis.showResult);
	const showScore = $derived(fieldVis.showScore);
	const showDocumentationScore = $derived(fieldVis.showDocumentationScore);
	const showObservation = $derived(fieldVis.showObservation);
	const showAppliedControls = $derived(fieldVis.showAppliedControls);
	const showTaskTemplates = $derived(fieldVis.showTaskTemplates);
	const showEvidences = $derived(fieldVis.showEvidences);
	const showRespondentAlignment = $derived(fieldVis.showRespondentAlignment);
	const showComments = $derived(fieldVis.showComments);
	const showStatus = $derived(fieldVis.showStatus);
	const showExtendedResult = $derived(fieldVis.showExtendedResult);

	// Single assignment — the URL param (params.id) IS the assignment ID
	let assignment = $derived(data.assignment);
	let assignmentStatus = $derived(assignment?.status ?? null);

	let isAuditor = $derived(viewerRole === 'auditor');

	// Back returns where the visit started, remembered per assignment for the tab.
	let cameFrom = $state<string | null>(null);
	afterNavigate(({ from, to, type }) => {
		const key = `assignmentBack:${to?.params?.id}`;
		const origin =
			type !== 'popstate' && from?.url && from.url.pathname !== to?.url.pathname
				? from.url.pathname + from.url.search
				: null;
		try {
			// The first origin wins, so links back here keep it.
			const stored = sessionStorage.getItem(key);
			if (!stored && origin) sessionStorage.setItem(key, origin);
			cameFrom = stored ?? origin ?? cameFrom;
		} catch {
			cameFrom ??= origin;
		}
	});
	const backHref = $derived(
		cameFrom ??
			(isAuditor ? `/compliance-assessments/${complianceAssessment.id}` : '/auditee-dashboard')
	);

	function isFieldEditable(fieldName: string): boolean {
		if (complianceAssessment.is_locked || complianceAssessment.status === 'in_review') return false;
		if (!isAuditor) {
			if (
				assignmentStatus === 'draft' ||
				assignmentStatus === 'submitted' ||
				assignmentStatus === 'closed'
			)
				return false;
		}
		return isFieldEditableHelper(complianceAssessment, fieldName, viewerRole);
	}

	const canEditResult = $derived(isFieldEditable('result'));
	const canEditScore = $derived(isFieldEditable('score'));
	const canEditDocumentationScore = $derived(isFieldEditable('documentation_score'));
	const canEditObservation = $derived(isFieldEditable('observation'));
	const canEditAppliedControls = $derived(isFieldEditable('applied_controls'));
	const canEditTaskTemplates = $derived(isFieldEditable('task_templates'));
	// The promise is the point of showing a respondent their tasks, so the panel rides
	// along with the flag rather than needing a page they cannot reach.
	const showCommitment = $derived(!!page.data?.featureflags?.commitment_management);
	const canEditEvidences = $derived(isFieldEditable('evidences'));
	const canEditAnswers = $derived(isFieldEditable('answers'));
	const canEditAlignment = $derived(isFieldEditable('respondent_alignment'));
	const canEditStatus = $derived(isFieldEditable('status'));
	const canEditExtendedResult = $derived(isFieldEditable('extended_result'));

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

	// The round's state, carried by a tag beside the title; the sentence stays as its tooltip.
	const assignmentStatusTag = $derived.by(() => {
		if (isAuditor) return null;
		switch (assignmentStatus) {
			case 'submitted':
				return {
					label: m.submitted(),
					description: m.assignmentSubmittedBanner(),
					icon: 'fa-clock',
					classes: 'preset-tonal-primary'
				};
			case 'closed':
				return {
					label: m.closed(),
					description: m.assignmentClosedBanner(),
					icon: 'fa-check-circle',
					classes: 'preset-tonal-success'
				};
			case 'changes_requested':
				return {
					label: m.reviewChangesRequested(),
					description: m.assignmentChangesRequestedBanner(),
					icon: 'fa-rotate-left',
					classes: 'preset-tonal-error'
				};
			case 'draft':
				return {
					label: m.assignmentAwaitingStart(),
					description: m.assignmentAwaitingStart(),
					icon: 'fa-hourglass',
					classes: 'preset-tonal-surface'
				};
			default:
				return null;
		}
	});

	// In a changes-requested round, the flag count rides on the state tag.
	const flagsInTag = $derived(assignmentStatus === 'changes_requested' && !!assignmentStatusTag);

	let observationExpanded = $state(false);
	let observationEl: HTMLElement | undefined = $state();
	let observationOverflows = $state(false);
	// Opening is offered only when the note is cut: a short note reads in full already.
	$effect(() => {
		const el = observationEl;
		const note = reviewerObservation;
		if (!el || !note) return;
		const measure = () =>
			(observationOverflows = note.includes('\n') || el.scrollWidth > el.clientWidth);
		measure();
		const observer = new ResizeObserver(measure);
		observer.observe(el);
		return () => observer.disconnect();
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

	function submissionErrorMessage(body: Record<string, any> | undefined): string {
		if (body?.error === 'evidenceRequired') {
			const names = (body.missing_evidence ?? [])
				.map((item: Record<string, any>) => item.name || item.ref_id || item.urn)
				.join(', ');
			return m.submissionBlockedMissingEvidence({ requirements: names });
		}
		return body?.error || m.submissionFailed();
	}

	let isSubmitting = $state(false);

	async function handleSubmitForReview() {
		if (!assignment || !canSubmit) return;

		const missing = missingEvidence.map((requirementAssessment) => ({
			id: requirementAssessment.id,
			label: requirementLabel(requirementOf(requirementAssessment))
		}));

		const modal: ModalSettings = {
			type: 'component',
			component: { ref: SubmitAssignmentModal, props: { missing } },
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
						await refreshAll();
						toastStore.trigger({
							message: m.statusUpdatedSuccessfully(),
							background: 'preset-filled-success-500',
							timeout: 3000
						});
					} else {
						toastStore.trigger({
							message: submissionErrorMessage(result.data?.submitBody),
							background: 'preset-filled-error-500',
							timeout: 8000
						});
					}
				} catch (error) {
					console.error('Error submitting assignment:', error);
					toastStore.trigger({
						message: m.anErrorOccurred(),
						background: 'preset-filled-error-500',
						timeout: 3000
					});
				} finally {
					isSubmitting = false;
				}
			}
		};
		modalStore.trigger(modal);
	}

	const canReview = $derived(isAuditor && assignmentStatus === 'submitted');

	async function transitionAssignment(status: string, reviewerObservation = '') {
		isSubmitting = true;
		try {
			const body = new FormData();
			body.set('status', status);
			body.set('reviewer_observation', reviewerObservation);
			const response = await fetch(`?/reviewAssignment`, { method: 'POST', body });
			const result = deserialize(await response.text());
			if (result.type === 'success' && result.data?.submitStatus === 200) {
				await applyAction(result);
				await refreshAll();
				toastStore.trigger({
					message: m.statusUpdatedSuccessfully(),
					background: 'preset-filled-success-500',
					timeout: 3000
				});
			} else {
				toastStore.trigger({
					message: result.data?.submitBody?.error || m.submissionFailed(),
					background: 'preset-filled-error-500',
					timeout: 5000
				});
			}
		} catch (error) {
			console.error('Error transitioning assignment:', error);
			toastStore.trigger({
				message: m.anErrorOccurred(),
				background: 'preset-filled-error-500',
				timeout: 3000
			});
		} finally {
			isSubmitting = false;
		}
	}

	function handleRequestChanges() {
		// The transition refuses without a note.
		modalStore.trigger({
			type: 'prompt',
			title: m.requestChanges(),
			body: m.reviewerObservation(),
			value: '',
			modalClasses: 'w-full max-w-2xl',
			valueAttr: {
				multiline: true,
				rows: 6,
				required: true,
				placeholder: m.reviewerObservationPlaceholder()
			},
			response: (note: string | false) => {
				if (note === false || !`${note ?? ''}`.trim()) return;
				transitionAssignment('changes_requested', `${note}`.trim());
			}
		});
	}

	function handleCloseAssignment() {
		modalStore.trigger({
			type: 'confirm',
			title: m.closeAssignment(),
			body: m.closeAssignmentConfirm(),
			response: (confirmed: boolean) => {
				if (confirmed) transitionAssignment('closed');
			}
		});
	}

	const requirementHashmap = $derived(
		Object.fromEntries(
			data.requirements.map((requirement: Record<string, any>) => [requirement.id, requirement])
		)
	);

	function requirementOf(requirementAssessment: Record<string, any>): Record<string, any> {
		return (
			requirementHashmap[
				requirementAssessment.requirement?.id ?? requirementAssessment.requirement
			] ?? requirementAssessment
		);
	}

	function requirementLabel(requirement: Record<string, any>): string {
		return requirement.display_short || requirement.ref_id || requirement.name || requirement.urn;
	}

	// An evidence with no file and no link is an empty shell; the API decides and
	// says so in `has_usable_evidence`, so this view cannot drift from it.
	function owesEvidence(requirementAssessment: Record<string, any>): boolean {
		if (!requirementOf(requirementAssessment).evidence_required) return false;
		return !requirementAssessment.has_usable_evidence;
	}

	// Hidden requirements are already out of `requirementAssessments`: the API filters them.
	let missingEvidence = $derived(
		requirementAssessments.filter(
			(requirementAssessment) =>
				requirementAssessment.assessable && owesEvidence(requirementAssessment)
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

	// Selecting another item brings the page back to its top.
	function goTo(index: number) {
		if (index < 0 || index >= navItems.length || index === currentIndex) return;
		currentIndex = index;
		window.scrollTo({ top: 0 });
	}

	// --- Progress (question-based when framework has questions, else result-based) ---
	// Framework-less assessable RAs count as 1 virtual auto-question for both roles,
	// so respondent and auditor see the same progress.
	function isFrameworklessAssessableItem(item: { data: Record<string, any> }): boolean {
		if (!item.data.requirement) return false;
		const q = item.data.requirement.questions;
		return (item.data.visible_questions ?? 0) === 0 && (q == null || Object.keys(q).length === 0);
	}
	const totalQuestions = $derived(
		assessableItems.reduce((sum, item) => {
			const visible = item.data.visible_questions ?? 0;
			if (isFrameworklessAssessableItem(item)) return sum + 1;
			return sum + visible;
		}, 0)
	);
	const answeredQuestions = $derived(
		assessableItems.reduce((sum, item) => {
			const answered = item.data.answered_questions ?? 0;
			if (isFrameworklessAssessableItem(item)) {
				return sum + (item.data.respondent_alignment ? 1 : 0);
			}
			return sum + answered;
		}, 0)
	);
	const useQuestionProgress = $derived(showAnswers && totalQuestions > 0);
	// Respondents track their own work: when the alignment field is in use,
	// the fallback progress counts their alignment answers, not the results
	// (which the auditor can set independently).
	const useAlignmentProgress = $derived(!isAuditor && showRespondentAlignment);
	// Mirrors the backend auto-map (alignment answer -> result) for ToC dots.
	const alignmentResultEquivalent: Record<string, string> = {
		yes: 'compliant',
		no: 'non_compliant',
		in_progress: 'partially_compliant',
		not_applicable: 'not_applicable'
	};

	const totalAssessable = $derived(assessableItems.length);
	// Per-item completion, mirroring the backend auditee-dashboard rules.
	// This page is respondent-oriented ON PURPOSE: the audit-level progress
	// mode (status-driven / score above minimum) does NOT apply here, since
	// respondents can neither see nor edit those fields. A question-bearing
	// requirement completes through its answers (whether or not they compute
	// a result), alignment-driven ones through the respondent's alignment
	// answer, the rest through the result.
	function isItemDone(item: { data: Record<string, any> }): boolean {
		const visible = item.data.visible_questions ?? 0;
		if (visible > 0) return (item.data.answered_questions ?? 0) >= visible;
		if (useAlignmentProgress) return Boolean(item.data.respondent_alignment);
		return item.data.result !== 'not_assessed';
	}
	const assessedCount = $derived(assessableItems.filter(isItemDone).length);
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

	// ToC dot for any section; an owed evidence keeps a compliant dot amber.
	function sectionDotColor(section: Record<string, any>): string {
		if (section.result === '__splash__') return '#a855f7';
		if (useQuestionProgress || section.hasVisibleQuestions) return section.questionColor;
		const result = useAlignmentProgress
			? alignmentResultEquivalent[section.alignment]
			: section.result;
		if (section.owesEvidence && result === 'compliant') return '#f59e0b';
		return complianceResultColorMap[result ?? ''] ?? '#d1d5db';
	}

	// Per-requirement question completion status for ToC dots
	function getQuestionStatus(item: { data: Record<string, any> }): string {
		const visible = item.data.visible_questions ?? 0;
		const answered = item.data.answered_questions ?? 0;
		// An owed evidence keeps the dot amber: submission would be refused.
		const complete = owesEvidence(item.data) ? '#f59e0b' : '#22c55e';
		// Framework-less assessable RA: reflect respondent_alignment state
		// for both respondent and auditor views so the ToC is accurate for everyone.
		if (isFrameworklessAssessableItem(item)) {
			return item.data.respondent_alignment ? complete : '#ef4444';
		}
		if (visible === 0) return complete; // no questions = complete
		if (answered >= visible) return complete; // all answered
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
		await refreshAll();
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

	// Which task's commitment panel is open: the table stays scannable and the
	// promise is one click away.
	let expandedTask = $state<string | null>(null);

	const REVIEW_STATES = [
		{ id: 'changes_requested', label: m.reviewChangesRequested(), color: '#ef4444' },
		{ id: 'resubmitted', label: m.reviewResubmitted(), color: '#f59e0b' },
		{ id: 'accepted', label: m.reviewAccepted(), color: '#10b981' }
	];
	const reviewStateMeta = (state: string | null | undefined) =>
		REVIEW_STATES.find((s) => s.id === state);

	// Half-finished flags stay on the reviewer's side until the round is sent back.
	const showReviewFlags = $derived(isAuditor || assignmentStatus !== 'submitted');
	function goToFirstFlagged() {
		tocFilterReview = 'changes_requested';
		const first = tocSections.find((s) => s.reviewState === 'changes_requested');
		if (first) goTo(first.index);
	}

	// A refused write (a locked round, a field the respondent may not set) would
	// otherwise re-render unflagged and read as a dead button.
	async function applied(res: Response): Promise<boolean> {
		const result = deserialize(await res.text());
		if (result.type === 'success') return true;
		toastStore.trigger({
			message: m.anErrorOccurred(),
			background: 'preset-filled-error-500',
			timeout: 3000
		});
		return false;
	}

	// One at a time: the buttons sit side by side, and two verdicts in flight land in
	// whatever order the server finishes them.
	let reviewPending = $state(false);

	async function setReviewState(requirementAssessment: Record<string, any>, state: string) {
		if (reviewPending) return;
		reviewPending = true;
		try {
			const next = requirementAssessment.review_state === state ? '' : state;
			const res = await fetch('?/updateRequirementAssessment', {
				method: 'POST',
				body: JSON.stringify({ id: requirementAssessment.id, review_state: next })
			});
			if (!(await applied(res))) return;
			await refreshAll();
		} finally {
			reviewPending = false;
		}
	}

	function scrollToComments() {
		document.getElementById('requirement-comments')?.scrollIntoView({ behavior: 'smooth' });
	}

	const taskStatusOptions = $derived(data.taskTemplateModel?.selectOptions?.status ?? []);

	async function updateTaskStatus(taskId: string, status: string) {
		const res = await fetch('?/updateTaskTemplateStatus', {
			method: 'POST',
			body: JSON.stringify({ id: taskId, status })
		});
		if (!(await applied(res))) return;
		await refreshAll();
	}

	function modalTaskTemplateCreateForm(createform: SuperForm<any>): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: createform,
				formAction: '?/createTaskTemplate',
				invalidateAll: true,
				model: data.taskTemplateModel,
				debug: false
			}
		};
		modalStore.trigger({
			type: 'component',
			component: modalComponent,
			title: m.addTaskTemplate()
		});
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
	// Entering a score is what makes a requirement scored (as in table mode).
	function markScored(requirementAssessment: Record<string, any>) {
		if (!requirementAssessment.is_scored) {
			requirementAssessment.is_scored = true;
			update(requirementAssessment, 'is_scored');
		}
	}
	let scoreForms = $state({});
	let docScoreForms = $state({});

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
		});
	});

	let accordionItems: Record<string, string[]> = $state(
		// svelte-ignore state_referenced_locally
		requirementAssessments.reduce(
			(acc, requirementAssessment) => {
				return { ...acc, [requirementAssessment.id]: [] };
			},
			{} as Record<string, string[]>
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
				reviewState: item.data.review_state,
				alignment: item.data.respondent_alignment,
				hasVisibleQuestions: (item.data.visible_questions ?? 0) > 0,
				owesEvidence: owesEvidence(item.data),
				questionColor: getQuestionStatus(item)
			};
		})
	);

	// ToC visibility and filtering
	let tocCollapsed = $state(false);
	let tocFilterResult = $state<string | null>(null);
	let tocFilterReview = $state<string | null>(null);
	const resultCounts = $derived(
		result_options.map((opt) => ({
			...opt,
			count: tocSections.filter((s) => s.result === opt.id).length
		}))
	);
	// Same entries the jump walks, so the count cannot promise a missing row.
	const changesRequestedCount = $derived(
		showReviewFlags ? tocSections.filter((s) => s.reviewState === 'changes_requested').length : 0
	);

	const reviewStateCounts = $derived(
		REVIEW_STATES.map((state) => ({
			...state,
			count: tocSections.filter((s) => s.reviewState === state.id).length
		}))
	);
	const filteredTocSections = $derived(
		tocSections.filter(
			(s) =>
				(!tocFilterResult || s.result === tocFilterResult) &&
				(!tocFilterReview || s.reviewState === tocFilterReview)
		)
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
	import CommentsPanel from '#lib/components/CommentsPanel/CommentsPanel.svelte';
	import CommitmentPanel from '#lib/components/CommitmentPanel/CommitmentPanel.svelte';
	import { onMount } from 'svelte';
	// Where the sticky header parks, and how tall it is: the ToC column hangs below it.
	let stickyTop = $state(0);
	let headerHeight = $state(0);

	onMount(() => {
		document.addEventListener('keydown', handleKeydown);
		const appbar = document.querySelector('.sticky.top-0.z-50') as HTMLElement | null;
		let cleanupAppbar: (() => void) | undefined;
		if (appbar) {
			const measure = () => (stickyTop = appbar.getBoundingClientRect().height);
			measure();
			const observer = new ResizeObserver(measure);
			observer.observe(appbar);
			window.addEventListener('resize', measure);
			cleanupAppbar = () => {
				observer.disconnect();
				window.removeEventListener('resize', measure);
			};
		}
		return () => {
			document.removeEventListener('keydown', handleKeydown);
			cleanupAppbar?.();
		};
	});
</script>

<div class="flex flex-col p-4">
	<div class="card px-6 py-4 bg-surface-50-950 flex flex-col shadow-lg w-full h-full space-y-3">
		<!-- Header, as in table-mode: navigation and actions above, ToC and progress below. -->
		<div
			class="sticky z-20 -mx-6 flex flex-col gap-2 border-b border-surface-200-800 bg-surface-50-950/80 px-6 py-2.5 backdrop-blur"
			style="top: {stickyTop}px"
			bind:clientHeight={headerHeight}
		>
			<div class="flex items-center gap-4">
				<div class="flex items-center gap-3 min-w-0">
					<a
						href={backHref}
						class="flex items-center gap-2 shrink-0 text-primary-800-200 hover:text-primary-600-400"
						data-testid="back-button"
					>
						<i class="fa-solid fa-arrow-left"></i>{m.back()}
					</a>
					{#if complianceAssessment.framework?.name}
						<span
							class="text-sm text-surface-600-400 truncate min-w-0 max-w-64"
							title={complianceAssessment.framework.name}
						>
							<i class="fa-solid fa-book mr-1"></i>{complianceAssessment.framework.name}
						</span>
					{/if}
					{#if assignmentStatusTag && flagsInTag && changesRequestedCount > 0}
						<button
							type="button"
							class="badge text-xs shrink-0 cursor-pointer {assignmentStatusTag.classes}"
							onclick={goToFirstFlagged}
							title="{assignmentStatusTag.description} {m.itemsNeedingChanges({
								count: changesRequestedCount
							})}"
							data-testid="assignment-status-tag"
						>
							<i class="fa-solid {assignmentStatusTag.icon} mr-1"></i>{assignmentStatusTag.label}
							<span class="ml-2 inline-flex items-center" data-testid="flagged-items-counter">
								<i class="fa-solid fa-flag mr-1"></i>{changesRequestedCount}
							</span>
						</button>
					{:else if assignmentStatusTag}
						<span
							class="badge text-xs shrink-0 {assignmentStatusTag.classes}"
							title={assignmentStatusTag.description}
							data-testid="assignment-status-tag"
						>
							<i class="fa-solid {assignmentStatusTag.icon} mr-1"></i>{assignmentStatusTag.label}
						</span>
					{/if}
					{#if changesRequestedCount > 0 && !flagsInTag}
						<button
							type="button"
							class="badge text-xs shrink-0 preset-tonal-error cursor-pointer"
							onclick={goToFirstFlagged}
							title={m.itemsNeedingChanges({ count: changesRequestedCount })}
							data-testid="flagged-items-counter"
						>
							<i class="fa-solid fa-flag mr-1"></i>{changesRequestedCount}
						</button>
					{/if}
				</div>
				{#snippet observationLine(clickable: boolean)}
					<i class="fa-solid fa-comment-dots mt-1 shrink-0" title={m.reviewerObservation()}></i>
					<span bind:this={observationEl} class="flex-1 min-w-0 truncate"
						>{reviewerObservation}</span
					>
					{#if clickable}
						<i
							class="fa-solid {observationExpanded
								? 'fa-chevron-up'
								: 'fa-chevron-down'} text-xs mt-1.5 shrink-0"
						></i>
					{/if}
				{/snippet}
				{#if reviewerObservation && observationOverflows}
					<Popover
						open={observationExpanded}
						onOpenChange={(e) => (observationExpanded = e.open)}
						positioning={{ placement: 'bottom', sameWidth: true }}
						autoFocus={false}
						closeOnInteractOutside={true}
					>
						<Popover.Trigger
							class="flex flex-1 min-w-0 items-start gap-2 text-sm text-left rounded-md px-3 py-1.5 bg-red-50 border-l-[3px] border-l-red-500 text-red-800 cursor-pointer hover:bg-red-100 transition-colors"
							title={observationExpanded ? m.collapse() : m.expand()}
							data-testid="reviewer-observation-strip"
						>
							{@render observationLine(true)}
						</Popover.Trigger>
						<Popover.Positioner class="z-50!">
							<Popover.Content
								class="card p-2 bg-surface-50-950 shadow-lg space-y-2 border border-surface-200"
								data-testid="reviewer-observation-full"
							>
								{#if observationExpanded}
									<div
										class="flex items-center gap-2 px-1 text-xs font-semibold text-error-600-400"
									>
										<i class="fa-solid fa-comment-dots"></i>{m.reviewerObservation()}
									</div>
									<hr class="border-surface-200" />
									<p class="px-1 text-sm whitespace-pre-line max-h-72 overflow-y-auto">
										{reviewerObservation}
									</p>
								{/if}
							</Popover.Content>
						</Popover.Positioner>
					</Popover>
				{:else if reviewerObservation}
					<div
						class="flex flex-1 min-w-0 items-start gap-2 text-sm rounded-md px-3 py-1.5 bg-red-50 border-l-[3px] border-l-red-500 text-red-800"
						data-testid="reviewer-observation-strip"
					>
						{@render observationLine(false)}
					</div>
				{/if}
				<div class="flex items-center gap-3 shrink-0 ml-auto">
					{#if !isAuditor && assignment?.events?.length > 0}
						<button
							type="button"
							class="btn btn-sm preset-tonal-surface whitespace-nowrap"
							onclick={openHistoryModal}
							title={m.viewHistory()}
							data-testid="events-history-button"
						>
							<i class="fa-solid fa-clock-rotate-left mr-2"></i>{m.eventsHistory()}
							<span class="ml-1 text-xs text-surface-500">{assignment.events.length}</span>
						</button>
					{/if}
					{#if canReview}
						<button
							class="btn btn-sm preset-tonal-error whitespace-nowrap"
							onclick={handleRequestChanges}
							disabled={isSubmitting}
							data-testid="request-changes-button"
						>
							<i class="fa-solid fa-rotate-left mr-2"></i>{m.requestChanges()}
						</button>
						<button
							class="btn btn-sm preset-filled-success-500 whitespace-nowrap"
							onclick={handleCloseAssignment}
							disabled={isSubmitting}
							data-testid="close-assignment-button"
						>
							{#if isSubmitting}
								<i class="fa-solid fa-spinner fa-spin mr-2"></i>
							{:else}
								<i class="fa-solid fa-check mr-2"></i>
							{/if}
							{m.closeAssignment()}
						</button>
					{/if}
					{#if canSubmit}
						<button
							class="btn btn-sm preset-filled-primary-500 whitespace-nowrap"
							onclick={handleSubmitForReview}
							disabled={isSubmitting}
							data-testid="submit-for-review-button"
						>
							{#if isSubmitting}
								<i class="fa-solid fa-spinner fa-spin mr-2"></i>
							{:else}
								<i class="fa-solid fa-paper-plane mr-2"></i>
							{/if}
							{m.submitForReview()}
						</button>
					{/if}
				</div>
			</div>
			<div class="flex items-center gap-4 flex-wrap border-t border-surface-100-900 pt-2">
				<button
					type="button"
					class="btn btn-sm shrink-0 border font-medium preset-tonal-surface border-surface-300-700"
					onclick={() => (tocCollapsed = !tocCollapsed)}
					aria-pressed={!tocCollapsed}
				>
					<i class="fa-solid {tocCollapsed ? 'fa-list-ul' : 'fa-angles-left'} mr-2"></i>
					{m.tableOfContents()}
				</button>
				{#if complianceAssessment.eta || complianceAssessment.due_date}
					<div class="flex items-center space-x-4 text-sm text-surface-600-400 shrink-0">
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
				<div class="flex flex-1 items-center space-x-3 min-w-[200px]">
					<div class="flex-1 bg-surface-200-800 rounded-full h-2">
						<div
							class="h-2 rounded-full transition-all duration-500 ease-out"
							style="width: {progressPercent}%; background: linear-gradient(90deg, var(--color-primary-500), var(--color-primary-400));"
						></div>
					</div>
					<span class="text-sm font-medium text-surface-600-400 whitespace-nowrap">
						{#if useQuestionProgress}
							{answeredQuestions}/{totalQuestions} {m.questions()} ({progressPercent}%)
						{:else}
							{assessedCount}/{totalAssessable} ({progressPercent}%)
						{/if}
					</span>
				</div>
			</div>
		</div>

		<!-- Read-only banner (only for CA-level locks, not assignment-level) -->
		{#if complianceAssessment.is_locked || complianceAssessment.status === 'in_review'}
			<div
				class="bg-surface-50-950 border border-yellow-200 border-l-[3px] border-l-yellow-500 rounded-lg px-5 py-3 flex items-center gap-3 shadow-sm"
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
		<div class="flex flex-row items-start gap-4">
			{#if !tocCollapsed}
				<!-- Table of contents column (child of the card, toggled from the header) -->
				<div
					class="w-72 flex-shrink-0 self-start sticky overflow-y-auto border-r border-surface-200-800 pr-2"
					style="top: {stickyTop + headerHeight}px; max-height: calc(100vh - {stickyTop +
						headerHeight}px - 1rem)"
				>
					<div class="px-2 py-2 flex flex-wrap gap-1 border-b border-surface-200-800">
						{#each resultCounts as opt}
							{#if opt.count > 0}
								<button
									class="px-2 py-1 text-[10px] rounded transition-colors flex items-center gap-1.5
								{tocFilterResult === opt.id
										? 'bg-surface-700-300 text-white font-semibold'
										: 'bg-surface-50-950 text-surface-700-300 hover:bg-surface-200-800 border border-surface-200-800'}"
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
						{#each reviewStateCounts as state}
							{#if state.count > 0 && showReviewFlags}
								<button
									class="px-2 py-1 text-[10px] rounded transition-colors flex items-center gap-1.5
								{tocFilterReview === state.id
										? 'bg-surface-700-300 text-white font-semibold'
										: 'bg-surface-50-950 text-surface-700-300 hover:bg-surface-200-800 border border-surface-200-800'}"
									onclick={() => (tocFilterReview = tocFilterReview === state.id ? null : state.id)}
									title={state.label}
								>
									<i class="fa-solid fa-flag text-[9px]" style="color: {state.color};"></i>
									{state.count}
								</button>
							{/if}
						{/each}
					</div>
					<nav class="p-2 space-y-0.5">
						{#each filteredTocSections as section}
							{#if section.result === '__section__'}
								<button
									class="w-full text-left px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-surface-400-600 mt-2 truncate
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
										? 'bg-primary-100 text-primary-800-200 font-semibold'
										: 'text-surface-600-400 hover:bg-surface-200-800'}"
									onclick={() => goTo(section.index)}
									title={section.owesEvidence
										? `${section.title} (${m.evidenceRequired()})`
										: section.title}
								>
									<span
										class="inline-block w-2 h-2 rounded-full flex-shrink-0"
										style="background-color: {sectionDotColor(section)};"
									></span>
									<span class="truncate">{section.title}</span>
									{#if showReviewFlags && reviewStateMeta(section.reviewState)}
										{@const meta = reviewStateMeta(section.reviewState)}
										<i
											class="fa-solid fa-flag text-[9px] ml-auto flex-shrink-0"
											style="color: {meta?.color};"
											title={meta?.label}
										></i>
									{/if}
								</button>
							{/if}
						{/each}
					</nav>
				</div>
			{/if}
			<div class="flex-1 min-w-0 flex flex-col space-y-4">
				<!-- Current item: splash screen or requirement assessment -->
				{#if currentSplashNode}
					<SplashCard
						name={currentSplashNode.name}
						description={currentSplashNode.description}
						id="current-requirement"
						class="card bg-surface-50-950 shadow-md"
					/>
				{:else if currentSectionNode}
					<div
						id="current-requirement"
						class="card bg-surface-100-900 shadow-sm border-l-4 border-l-gray-400 px-6 py-3"
					>
						<h3 class="text-lg font-semibold text-surface-700-300">{currentSectionNode.name}</h3>
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
						class="card bg-surface-50-950 shadow-md border-t-[3px] border-t-orange-400 px-6 py-5 flex flex-col space-y-4"
					>
						<!-- Requirement title -->
						<div class="flex items-start justify-between gap-4">
							<div>
								<h3 class="text-xl font-semibold text-orange-600">
									{getTitle(requirementAssessment)}
								</h3>
								{#if requirement.ref_id && requirement.name}
									<p class="text-sm text-surface-600-400 mt-0.5">{requirement.ref_id}</p>
								{/if}
							</div>
							{#if isAuditor}
								<div class="flex items-center gap-1 flex-shrink-0">
									<button
										type="button"
										class="btn btn-sm {requirementAssessment.review_state === 'changes_requested'
											? 'preset-filled-error-500'
											: 'preset-tonal-surface'}"
										onclick={() => setReviewState(requirementAssessment, 'changes_requested')}
										disabled={reviewPending}
										title={requirementAssessment.review_state === 'changes_requested'
											? m.removeChangeRequestFlag()
											: m.flagForChangeRequest()}
									>
										<i class="fa-solid fa-flag mr-1"></i>{requirementAssessment.review_state ===
										'changes_requested'
											? m.removeChangeRequestFlag()
											: m.flagForChangeRequest()}
									</button>
									<button
										type="button"
										class="btn btn-sm {requirementAssessment.review_state === 'accepted'
											? 'preset-filled-success-500'
											: 'preset-tonal-surface'}"
										onclick={() => setReviewState(requirementAssessment, 'accepted')}
										disabled={reviewPending}
										aria-label={m.markAsAccepted()}
										aria-pressed={requirementAssessment.review_state === 'accepted'}
										title={m.markAsAccepted()}
									>
										<i class="fa-solid fa-check"></i>
									</button>
								</div>
							{:else if showReviewFlags && reviewStateMeta(requirementAssessment.review_state)}
								{@const meta = reviewStateMeta(requirementAssessment.review_state)}
								<span
									class="badge text-xs flex-shrink-0"
									style="background-color: {meta?.color}1a; color: {meta?.color};"
								>
									<i class="fa-solid fa-flag mr-1"></i>{meta?.label}
								</span>
							{/if}
						</div>
						{#if showReviewFlags && !isAuditor && requirementAssessment.review_state === 'changes_requested'}
							<div
								class="bg-surface-100-900 rounded-md px-4 py-2 flex items-center justify-between gap-3 text-sm text-surface-700-300"
							>
								<span
									><i class="fa-solid fa-flag text-red-500 mr-2"
									></i>{m.changesRequestedItemHint()}</span
								>
								{#if page.data?.featureflags?.comments && showComments}
									<button
										type="button"
										class="btn btn-sm preset-tonal-error"
										onclick={scrollToComments}
									>
										{m.seeComments()}
									</button>
								{/if}
							</div>
						{/if}

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
										<p class="font-medium">
											<i class="fa-solid fa-pencil mr-1"></i>{m.annotation()}
										</p>
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
									{#if showAnswers && requirement.questions != null && Object.keys(requirement.questions).length !== 0}
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

									<!-- Auto-alignment question (when no framework questions) -->
									{#if shouldShowAutoQuestion(requirement, viewerRole, complianceAssessment)}
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
												disabled={!canEditAlignment}
												onChange={(_urn, choiceUrn) => {
													const newAlignment = alignmentValueFromChoiceUrn(choiceUrn);
													requirementAssessment.respondent_alignment = newAlignment;
													update(requirementAssessment, 'respondent_alignment');
												}}
											/>
										</div>
									{/if}

									<!-- Auditor badge: respondent's alignment answer -->
									{#if viewerRole === 'auditor' && showRespondentAlignment && requirementAssessment.respondent_alignment}
										<div class="flex flex-col items-center my-2">
											<p class="text-xs italic text-surface-600">
												{m.respondentAnswered()}
											</p>
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

									<!-- Status -->
									{#if showStatus}
										<div class="flex flex-col items-center w-full my-2">
											<p class="flex items-center font-semibold text-purple-600 italic">
												{m.status()}
											</p>
											<RadioGroup
												possibleOptions={status_options}
												key="id"
												labelKey="label"
												field="status"
												disabled={!canEditStatus}
												initialValue={requirementAssessment.status ?? 'to_do'}
												onChange={(newValue) => {
													requirementAssessment.status = newValue;
													update(requirementAssessment, 'status');
												}}
											/>
										</div>
									{/if}

									<!-- Result -->
									{#if showResult}
										<div class="flex flex-col items-center w-full my-2" data-testid="result-field">
											<p class="flex items-center font-semibold text-purple-600 italic">
												{m.result()}
											</p>
											{#if hasComputedResult(requirement.questions)}
												<span
													class="badge text-sm font-semibold"
													style={resultBadgeStyle(requirementAssessment.result)}
												>
													{safeTranslate(requirementAssessment.result)}
												</span>
											{:else}
												<RadioGroup
													possibleOptions={requirementResultOptions(
														page.data.settings?.disable_partially_compliant_result,
														requirementAssessment.result
													)}
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

									<!-- Extended result -->
									{#if showExtendedResult}
										<div class="flex flex-col items-center w-full my-2">
											<p class="flex items-center font-semibold text-purple-600 italic">
												{m.extendedResult()}
											</p>
											<RadioGroup
												possibleOptions={extended_result_options}
												key="id"
												labelKey="label"
												field="extended_result"
												disabled={!canEditExtendedResult}
												initialValue={requirementAssessment.extended_result ?? null}
												onChange={(newValue) => {
													const next =
														requirementAssessment.extended_result === newValue ? null : newValue;
													requirementAssessment.extended_result = next;
													update(requirementAssessment, 'extended_result');
												}}
											/>
										</div>
									{/if}

									<!-- Score -->
									{#if showScore}
										<div class="flex flex-col w-full place-items-center">
											{#if complianceAssessment.scoring_enabled && hasComputedScore(requirement.questions)}
												{@const raMin =
													requirementAssessment.effective_min_score ??
													complianceAssessment.min_score}
												{@const raMax =
													requirementAssessment.effective_max_score ??
													complianceAssessment.max_score}
												<div class="flex flex-row items-center space-x-4">
													<span class="font-medium">{m.score()}</span>
													<div class="shrink-0 relative">
														<Progress
															value={formatScoreValue(
																requirementAssessment.score,
																raMax,
																false,
																raMin
															)}
															min={0}
															max={100}
														>
															<Progress.Circle class="[--size:--spacing(10)]">
																<Progress.CircleTrack />
																<Progress.CircleRange
																	class={displayScoreColor(
																		requirementAssessment.score,
																		raMax,
																		false,
																		raMin
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
												{@const raMin =
													requirementAssessment.effective_min_score ??
													complianceAssessment.min_score}
												{@const raMax =
													requirementAssessment.effective_max_score ??
													complianceAssessment.max_score}
												{@const raScoresDef =
													requirementAssessment.effective_scores_definition ??
													complianceAssessment.scores_definition}
												<ScorePair>
													{#snippet implementation()}
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
																markScored(requirementAssessment);
																updateScore(requirementAssessment);
															}}
															disabled={!canEditScore}
														/>
													{/snippet}
													{#snippet documentation()}
														{#if showDocumentationScore}
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
																	markScored(requirementAssessment);
																	updateScore(requirementAssessment);
																}}
																disabled={!canEditDocumentationScore}
															/>
														{/if}
													{/snippet}
												</ScorePair>
											{/if}
										</div>
									{/if}

									<Accordion
										multiple
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
																<i class="fa-solid fa-hand-pointer mr-2"
																></i>{m.selectAppliedControls()}
															</button>
														</div>
													{/if}
													<div class="flex flex-wrap space-x-2 items-center">
														{#each requirementAssessment.applied_controls ?? [] as ac}
															<p class="p-2">
																<Anchor
																	class="anchor"
																	href="/applied-controls/{ac.id}"
																	label={ac.str}
																>
																	<i class="fa-solid fa-fire-extinguisher mr-2"></i>{ac.str}
																</Anchor>
															</p>
														{/each}
													</div>
												</Accordion.ItemContent>
											</Accordion.Item>
										{/if}

										<!-- Tasks -->
										{#if showTaskTemplates}
											<Accordion.Item value="taskTemplates">
												<Accordion.ItemTrigger
													class="flex w-full items-center cursor-pointer"
													data-testid="task-templates-accordion-trigger"
												>
													<p class="flex flex-1 items-center space-x-2 text-left">
														<span>{m.taskTemplates()}</span>
														{#if requirementAssessment.task_templates != null}
															<span class="badge preset-tonal-primary"
																>{requirementAssessment.task_templates.length}</span
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
													{#if canEditTaskTemplates}
														<div class="flex flex-row space-x-2 items-center mb-2">
															<button
																class="btn preset-filled-primary-500 self-start"
																type="button"
																data-testid="add-task-template-button"
																onclick={() =>
																	modalTaskTemplateCreateForm(
																		requirementAssessment.taskTemplateCreateForm
																	)}
															>
																<i class="fa-solid fa-plus mr-2"></i>{m.addTaskTemplate()}
															</button>
															<button
																class="btn preset-filled-secondary-500 self-start"
																type="button"
																onclick={() =>
																	modalUpdateForm(requirementAssessment, 'selectTaskTemplates')}
															>
																<i class="fa-solid fa-hand-pointer mr-2"></i>{m.taskTemplates()}
															</button>
														</div>
													{/if}
													{#if !requirementAssessment.task_templates?.length}
														<p class="text-sm text-surface-600-400 p-2">{m.noTaskTemplates()}</p>
													{:else}
														<table class="w-full text-sm">
															<thead class="text-surface-600-400 border-b border-surface-200-800">
																<tr>
																	<th class="text-left font-medium py-1">{m.name()}</th>
																	<th class="text-left font-medium py-1">{m.eta()}</th>
																	<th class="text-left font-medium py-1">{m.status()}</th>
																	{#if showCommitment}
																		<th class="text-left font-medium py-1">{m.commitment()}</th>
																		<th class="w-8"></th>
																	{/if}
																</tr>
															</thead>
															<tbody>
																{#each requirementAssessment.task_templates ?? [] as task}
																	<tr class="border-b border-surface-100-900">
																		<td class="py-2">
																			<i class="fa-solid fa-list-check mr-2 text-surface-500"
																			></i>{task.str}
																		</td>
																		<td class="py-2">{task.task_date ?? '--'}</td>
																		<td class="py-2">
																			{#if task.status && canEditTaskTemplates}
																				<select
																					class="select select-sm text-xs w-36"
																					aria-label={m.status()}
																					value={task.status}
																					onchange={(e) =>
																						updateTaskStatus(task.id, e.currentTarget.value)}
																				>
																					{#each taskStatusOptions as option}
																						<option value={option.value}
																							>{safeTranslate(option.label)}</option
																						>
																					{/each}
																				</select>
																			{:else}
																				{task.status ? safeTranslate(task.status) : '--'}
																			{/if}
																		</td>
																		{#if showCommitment}
																			<td class="py-2">
																				{task.commitment_state && task.commitment_state !== '--'
																					? safeTranslate(task.commitment_state)
																					: '--'}
																				{#if task.committed_eta}
																					<span class="text-xs text-surface-600-400"
																						>({task.committed_eta})</span
																					>
																				{/if}
																			</td>
																			<td class="py-2 text-right">
																				<button
																					type="button"
																					class="btn-icon btn-icon-sm preset-tonal-surface"
																					aria-label={m.commitment()}
																					onclick={() =>
																						(expandedTask =
																							expandedTask === task.id ? null : task.id)}
																				>
																					<i
																						class="fa-solid {expandedTask === task.id
																							? 'fa-chevron-up'
																							: 'fa-chevron-down'}"
																					></i>
																				</button>
																			</td>
																		{/if}
																	</tr>
																	{#if showCommitment && expandedTask === task.id}
																		<tr>
																			<td colspan="5" class="pb-3">
																				<CommitmentPanel
																					urlModel="task-templates"
																					object={task}
																					readOnly={!canEditTaskTemplates}
																				/>
																			</td>
																		</tr>
																	{/if}
																{/each}
															</tbody>
														</table>
													{/if}
												</Accordion.ItemContent>
											</Accordion.Item>
										{/if}

										<!-- Evidence -->
										{#if showEvidences}
											<Accordion.Item value="evidence">
												<Accordion.ItemTrigger
													class="flex w-full items-center cursor-pointer"
													data-testid="evidence-accordion-trigger"
												>
													<p class="flex flex-1 items-center space-x-2 text-left">
														<span>{m.evidence()}</span>
														{#if requirementAssessment.evidences != null}
															<span class="badge preset-tonal-primary" data-testid="evidence-count"
																>{requirementAssessment.evidences.length}</span
															>
														{/if}
														{#if requirement.evidence_required}
															<span
																class="badge {owesEvidence(requirementAssessment)
																	? 'preset-tonal-error'
																	: 'preset-tonal-success'}"
																data-testid="evidence-required-badge"
															>
																{owesEvidence(requirementAssessment)
																	? m.evidenceRequired()
																	: m.evidenceProvided()}
															</span>
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
									</Accordion>

									<!-- Observation (always visible, never collapsible) -->
									{#if showObservation}
										<div class="flex flex-col w-full space-y-1 pt-2">
											<p class="font-medium text-sm">{m.observation()}</p>
											<TableMarkdownField
												bind:value={requirementAssessment.observation}
												disabled={!canEditObservation}
												onSave={async (newValue) => {
													await update(requirementAssessment, 'observation');
													requirementAssessment.observationBuffer = newValue;
												}}
											/>
										</div>
									{/if}
								</form>
							{/key}
						{/if}
						{#if page.data?.featureflags?.comments && showComments}
							<div id="requirement-comments">
								<CommentsPanel
									parentType="requirement_assessment"
									parentId={requirementAssessment.id}
								/>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Previous / Next navigation (shown for both splash and assessment items) -->
				{#if currentSplashNode || currentItem}
					<div class="flex items-center justify-between card bg-surface-50-950 shadow-sm px-5 py-3">
						<button
							class="btn preset-tonal-surface"
							disabled={currentIndex === 0}
							onclick={() => goTo(currentIndex - 1)}
						>
							<i class="fa-solid fa-arrow-left mr-2"></i>
							{m.previous()}
						</button>
						<span class="text-sm text-surface-600-400">
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
						<div
							class="w-16 h-16 rounded-2xl bg-surface-200-800 flex items-center justify-center mb-5"
						>
							<i class="fa-solid fa-clipboard-check text-2xl text-surface-300-700"></i>
						</div>
						<p class="text-surface-400-600">{m.noAuditAssignments()}</p>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>

<!-- History Modal -->
{#if showHistoryModal && assignment?.events?.length > 0}
	<div class="fixed inset-0 bg-black/50 z-40" onclick={closeHistoryModal} role="presentation"></div>
	<div class="fixed inset-0 z-50 flex items-center justify-center p-4">
		<div
			class="bg-surface-50-950 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col"
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
					<span class="text-sm text-surface-600-400">
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
													: 'bg-surface-300-700'}"
								></div>
								<div class="w-px flex-1 bg-surface-200-800 mt-1"></div>
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
														: 'bg-surface-200-800 text-surface-700-300'}"
									>
										{safeTranslate(event.event_type)}
									</span>
									<span class="text-surface-600-400 text-xs">
										{formatEventActor(event.event_actor)}
									</span>
								</div>
								<span class="text-surface-400-600 text-xs">
									{formatDate(new Date(event.created_at), true, getLocale())}
								</span>
								{#if event.event_notes}
									<div
										class="mt-1.5 text-sm text-surface-700-300 whitespace-pre-line bg-surface-100-900 border border-surface-100-900 rounded-md px-3 py-2"
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
			<div class="p-4 border-t bg-surface-100-900 rounded-b-lg">
				<button class="btn preset-filled-surface-900-100 w-full" onclick={closeHistoryModal}>
					{m.close()}
				</button>
			</div>
		</div>
	</div>
{/if}
