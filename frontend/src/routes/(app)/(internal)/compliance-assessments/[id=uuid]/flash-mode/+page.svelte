<script lang="ts">
	import { complianceResultTailwindColorMap } from '$lib/utils/constants';
	import RadioGroup from '$lib/components/Forms/RadioGroup.svelte';
	import Question from '$lib/components/Forms/Question.svelte';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let isReadOnly = $derived(
		data.compliance_assessment.is_locked || data.compliance_assessment.status === 'in_review'
	);

	const possible_options = [
		{ id: 'not_assessed', label: m.notAssessed() },
		{ id: 'non_compliant', label: m.nonCompliant() },
		{ id: 'partially_compliant', label: m.partiallyCompliant() },
		{ id: 'compliant', label: m.compliant() },
		{ id: 'not_applicable', label: m.notApplicable() }
	];

	const requirementHashmap = Object.fromEntries(
		data.requirements.map((requirement: Record<string, any>) => [requirement.id, requirement])
	);

	// Build unified navigation: assessable items + splash nodes, ordered by order_id
	type NavItem =
		| { type: 'assessment'; data: (typeof data.requirement_assessments)[0] }
		| { type: 'splash'; data: Record<string, any> };

	const assessmentItems: NavItem[] = data.requirement_assessments
		.filter((ra: Record<string, any>) => ra.name || ra.description)
		.map((ra: Record<string, any>) => ({ type: 'assessment' as const, data: ra }));

	const splashItems: NavItem[] = data.requirements
		.filter((r: Record<string, any>) => r.display_mode === 'splash')
		.map((r: Record<string, any>) => ({ type: 'splash' as const, data: r }));

	// Merge and sort by order_id
	const navItems: NavItem[] = [...assessmentItems, ...splashItems].sort((a, b) => {
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

	// Only assessable items count for progress
	const assessableItems = navItems.filter((item) => item.type === 'assessment');

	let currentIndex = $state(0);
	let currentNavItem = $derived(navItems[currentIndex]);
	let currentRequirementAssessment = $derived(
		currentNavItem?.type === 'assessment' ? currentNavItem.data : null
	);
	let currentSplashNode = $derived(currentNavItem?.type === 'splash' ? currentNavItem.data : null);

	let color = $derived(
		currentRequirementAssessment
			? complianceResultTailwindColorMap[currentRequirementAssessment.result]
			: undefined
	);

	let requirement = $derived(
		currentRequirementAssessment
			? requirementHashmap[currentRequirementAssessment.requirement?.id]
			: currentSplashNode
	);
	let parent = $derived(
		requirement
			? data.requirements.find((req: Record<string, any>) => req.urn === requirement.parent_urn)
			: null
	);

	let title = $derived(
		requirement?.display_short
			? requirement.display_short
			: parent?.display_short
				? parent.display_short
				: (parent?.description ?? '')
	);

	// Progress tracking (only assessable items count)
	let assessedCount = $derived(
		assessableItems.filter(
			(item) =>
				item.type === 'assessment' && item.data.result && item.data.result !== 'not_assessed'
		).length
	);
	let progressPercent = $derived(
		assessableItems.length > 0 ? Math.round((assessedCount / assessableItems.length) * 100) : 0
	);
	let currentProgressPercent = $derived(
		navItems.length > 0 ? ((currentIndex + 1) / navItems.length) * 100 : 0
	);

	// Slide direction for transitions
	let slideDirection = $state<'next' | 'prev'>('next');
	let transitionKey = $state(0);

	function nextItem() {
		flushObservation();
		slideDirection = 'next';
		if (currentIndex < navItems.length - 1) {
			currentIndex += 1;
		} else {
			currentIndex = 0;
		}
		transitionKey++;
	}

	function previousItem() {
		flushObservation();
		slideDirection = 'prev';
		if (currentIndex > 0) {
			currentIndex -= 1;
		} else {
			currentIndex = navItems.length - 1;
		}
		transitionKey++;
	}

	// svelte-ignore state_referenced_locally
	let result = $state(currentRequirementAssessment?.result ?? null);
	// svelte-ignore state_referenced_locally
	let observation = $state(currentRequirementAssessment?.observation ?? '');
	$effect(() => {
		result = currentRequirementAssessment?.result ?? null;
		observation = currentRequirementAssessment?.observation ?? '';
	});

	// Debounce timer for observation saves
	let observationTimer: ReturnType<typeof setTimeout> | null = null;

	function flushObservation() {
		if (observationTimer) {
			clearTimeout(observationTimer);
			observationTimer = null;
			saveObservation(observation);
		}
	}

	function saveObservation(value: string) {
		currentRequirementAssessment.observation = value;
		const form = document.getElementById('flashModeForm');
		const formData = {
			id: currentRequirementAssessment.id,
			observation: value
		};
		fetch(form!.action, {
			method: 'POST',
			body: JSON.stringify(formData)
		});
	}

	function handleObservationInput(value: string) {
		observation = value;
		if (observationTimer) clearTimeout(observationTimer);
		observationTimer = setTimeout(() => saveObservation(value), 500);
	}

	function saveAnswer(urn: string, newAnswer: any) {
		if (!currentRequirementAssessment) return;
		if (!currentRequirementAssessment.answers) currentRequirementAssessment.answers = {};
		currentRequirementAssessment.answers[urn] = newAnswer;
		const form = document.getElementById('flashModeForm');
		fetch(form!.action, {
			method: 'POST',
			body: JSON.stringify({
				id: currentRequirementAssessment.id,
				answers: { [urn]: newAnswer }
			})
		});
	}

	let currentQuestions = $derived(
		currentRequirementAssessment
			? (requirementHashmap[currentRequirementAssessment.requirement?.id]?.questions ?? null)
			: null
	);
	let hasQuestions = $derived(currentQuestions != null && Object.keys(currentQuestions).length > 0);

	function updateResult(newResult: string | null) {
		currentRequirementAssessment.result = newResult;
		result = newResult;
		const form = document.getElementById('flashModeForm');
		const formData = {
			id: currentRequirementAssessment.id,
			result: newResult
		};
		fetch(form!.action, {
			method: 'POST',
			body: JSON.stringify(formData)
		});
	}

	// Navigation state
	let showNavigation = $state(false);
	let jumpToInput = $state('');

	function jumpToItem(index: number) {
		flushObservation();
		if (index >= 0 && index < navItems.length) {
			slideDirection = index > currentIndex ? 'next' : 'prev';
			currentIndex = index;
			showNavigation = false;
			jumpToInput = '';
			transitionKey++;
		}
	}

	function handleJumpSubmit() {
		const targetIndex = parseInt(jumpToInput) - 1;
		jumpToItem(targetIndex);
	}

	function handleKeydown(event: KeyboardEvent) {
		const key = event.key.toLowerCase();
		const target = event.target as HTMLElement | null;
		const tag = target?.tagName?.toLowerCase();
		const isEditable = target?.isContentEditable;
		if (
			(tag === 'input' || tag === 'textarea' || tag === 'select' || isEditable) &&
			target?.id !== 'jumpInput'
		) {
			return;
		}
		if (key === 'n' || key === 'l') {
			event.preventDefault();
			nextItem();
		} else if (key === 'p' || key === 'h') {
			event.preventDefault();
			previousItem();
		} else if (event.key === 'g') {
			showNavigation = !showNavigation;
			if (showNavigation) {
				setTimeout(() => {
					document.getElementById('jumpInput')?.focus();
				}, 0);
			}
		} else if (key === 'escape') {
			showNavigation = false;
			jumpToInput = '';
		}
	}

	// Color mapping for the left accent bar
	const resultAccentColorMap: Record<string, string> = {
		not_assessed: '#d1d5db',
		partially_compliant: '#fbbf24',
		non_compliant: '#f87171',
		compliant: '#4ade80',
		not_applicable: '#1e293b'
	};
	let accentColor = $derived(
		currentSplashNode
			? '#a855f7'
			: (resultAccentColorMap[currentRequirementAssessment?.result ?? ''] ?? '#d1d5db')
	);
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="flash-mode-container">
	<div class="flash-card" style="--accent: {accentColor}">
		{#if currentNavItem}
			<!-- Top bar: back link + progress -->
			<div class="flash-header">
				<a href="/compliance-assessments/{data.compliance_assessment.id}" class="back-link">
					<i class="fa-solid fa-arrow-left"></i>
					<span>{m.goBackToAudit()}</span>
				</a>

				<div class="header-right">
					<span class="progress-stat">
						<i class="fa-solid fa-check text-green-400 text-[10px]"></i>
						{assessedCount}/{assessableItems.length}
					</span>
					<div class="relative">
						<button
							class="counter-btn"
							onclick={() => (showNavigation = !showNavigation)}
							title="Click to jump to specific item (or press G)"
						>
							<span class="counter-current">{currentIndex + 1}</span>
							<span class="counter-sep">/</span>
							<span class="counter-total">{navItems.length}</span>
							<kbd>G</kbd>
						</button>

						{#if showNavigation}
							<div class="jump-popover">
								<div class="jump-popover-inner">
									<div class="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
										Jump to item
									</div>
									<div class="flex gap-2">
										<input
											id="jumpInput"
											bind:value={jumpToInput}
											type="number"
											min="1"
											max={navItems.length}
											placeholder="#"
											class="jump-input"
											onkeydown={(e) => {
												if (e.key === 'Enter') {
													e.preventDefault();
													handleJumpSubmit();
												}
											}}
										/>
										<button class="jump-go-btn" onclick={handleJumpSubmit}>
											<i class="fa-solid fa-arrow-right"></i>
										</button>
									</div>
									<div class="text-[10px] text-gray-400 mt-2">
										Enter to jump &middot; Esc to close
									</div>
								</div>
							</div>
						{/if}
					</div>
				</div>
			</div>

			<!-- Progress bar -->
			<div class="progress-track">
				<div class="progress-fill-assessed" style="width: {progressPercent}%"></div>
				<div class="progress-cursor" style="left: {currentProgressPercent}%"></div>
			</div>

			<!-- Read-only banner -->
			{#if isReadOnly}
				<div class="readonly-banner">
					<i class="fa-solid fa-lock"></i>
					<span>
						{data.compliance_assessment.is_locked
							? m.lockedAssessmentMessage()
							: m.assessmentInReviewMessage()}
					</span>
				</div>
			{/if}

			<!-- Main content area with slide transition -->
			<div class="flash-body">
				{#key transitionKey}
					<div
						class="flash-content"
						class:slide-in-right={slideDirection === 'next'}
						class:slide-in-left={slideDirection === 'prev'}
					>
						{#if currentSplashNode}
							<!-- Splash screen: full-page markdown -->
							{#if currentSplashNode.name}
								<div class="content-section-label flex items-center gap-2">
									<i class="fa-solid fa-display text-purple-400 text-sm"></i>
									{currentSplashNode.name}
								</div>
							{/if}
							<div class="content-description">
								<MarkdownRenderer content={currentSplashNode.description} />
							</div>
						{:else if currentRequirementAssessment}
							<div class="content-section-label">{title}</div>

							{#if currentRequirementAssessment.description}
								<div class="content-description">
									<MarkdownRenderer content={currentRequirementAssessment.description} />
								</div>
							{/if}

							{#if requirement?.annotation}
								<div class="content-annotation">
									<div class="annotation-bar"></div>
									<MarkdownRenderer content={requirement.annotation} />
								</div>
							{/if}

							{#if hasQuestions}
								<div class="mt-4">
									<Question
										questions={currentQuestions}
										initialValue={currentRequirementAssessment.answers ?? {}}
										field="answers"
										disabled={isReadOnly}
										onChange={saveAnswer}
									/>
								</div>
							{/if}
						{/if}
					</div>
				{/key}
			</div>

			<!-- Controls -->
			<div class="flash-controls">
				{#if currentRequirementAssessment}
					<form id="flashModeForm" action="?/updateRequirementAssessment" method="post">
						<RadioGroup
							possibleOptions={possible_options}
							initialValue={currentRequirementAssessment.result}
							classes="w-full"
							colorMap={complianceResultTailwindColorMap}
							disabled={isReadOnly}
							field="result"
							onChange={(newValue) => {
								const newResult = result === newValue ? 'not_assessed' : newValue;
								updateResult(newResult);
							}}
							key="id"
							labelKey="label"
						/>
					</form>

					<textarea
						class="observation-textarea"
						rows="2"
						placeholder="{m.observation()}..."
						value={observation}
						disabled={isReadOnly}
						oninput={(e) => handleObservationInput(e.currentTarget.value)}
					></textarea>
				{/if}

				<div class="nav-row">
					<button class="nav-btn nav-btn-prev" onclick={previousItem}>
						<i class="fa-solid fa-chevron-left text-xs"></i>
						<span>{m.previous()}</span>
						<kbd>H</kbd>
					</button>
					<button class="nav-btn nav-btn-next" onclick={nextItem}>
						<span>{m.next()}</span>
						<i class="fa-solid fa-chevron-right text-xs"></i>
						<kbd>L</kbd>
					</button>
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	/* ── Layout ── */
	.flash-mode-container {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		padding: 1.5rem;
		background: linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 100%);
	}

	.flash-card {
		display: flex;
		flex-direction: column;
		width: 100%;
		max-width: 56rem;
		min-height: 600px;
		max-height: 90vh;
		background: #fff;
		border-radius: 1rem;
		box-shadow:
			0 1px 3px rgba(0, 0, 0, 0.06),
			0 8px 24px rgba(0, 0, 0, 0.08);
		overflow: hidden;
		border-left: 4px solid var(--accent);
		transition: border-color 0.3s ease;
	}

	/* ── Header ── */
	.flash-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.875rem 1.25rem;
		border-bottom: 1px solid #f1f5f9;
	}

	.back-link {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.8125rem;
		font-weight: 500;
		color: #64748b;
		text-decoration: none;
		transition: color 0.15s;
	}
	.back-link:hover {
		color: #334155;
	}

	.header-right {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.progress-stat {
		font-size: 0.75rem;
		color: #94a3b8;
		font-weight: 500;
		letter-spacing: 0.01em;
	}

	.counter-btn {
		display: flex;
		align-items: center;
		gap: 0.125rem;
		padding: 0.25rem 0.5rem;
		border-radius: 0.375rem;
		border: 1px solid #e2e8f0;
		background: #f8fafc;
		font-size: 0.8125rem;
		cursor: pointer;
		transition: all 0.15s;
		font-variant-numeric: tabular-nums;
	}
	.counter-btn:hover {
		background: #f1f5f9;
		border-color: #cbd5e1;
	}
	.counter-current {
		font-weight: 700;
		color: #1e293b;
	}
	.counter-sep {
		color: #cbd5e1;
		margin: 0 0.0625rem;
	}
	.counter-total {
		color: #94a3b8;
	}
	.counter-btn kbd {
		margin-left: 0.375rem;
		font-size: 0.625rem;
		padding: 0.0625rem 0.25rem;
		border-radius: 0.1875rem;
		background: #e2e8f0;
		color: #94a3b8;
		font-family: inherit;
		line-height: 1.4;
	}

	/* ── Progress bar ── */
	.progress-track {
		height: 3px;
		background: #f1f5f9;
		position: relative;
		flex-shrink: 0;
	}
	.progress-fill-assessed {
		position: absolute;
		top: 0;
		left: 0;
		height: 100%;
		background: #4ade80;
		transition: width 0.4s cubic-bezier(0.22, 1, 0.36, 1);
		border-radius: 0 2px 2px 0;
	}
	.progress-cursor {
		position: absolute;
		top: -2px;
		width: 7px;
		height: 7px;
		background: #3b82f6;
		border-radius: 50%;
		transform: translateX(-50%);
		transition: left 0.3s cubic-bezier(0.22, 1, 0.36, 1);
		box-shadow:
			0 0 0 2px #fff,
			0 0 0 3px rgba(59, 130, 246, 0.3);
	}

	/* ── Read-only ── */
	.readonly-banner {
		display: flex;
		align-items: center;
		gap: 0.625rem;
		margin: 0.75rem 1.25rem 0;
		padding: 0.5rem 0.75rem;
		background: #fffbeb;
		border: 1px solid #fde68a;
		border-radius: 0.5rem;
		font-size: 0.8125rem;
		font-weight: 500;
		color: #92400e;
	}

	/* ── Body / Content ── */
	.flash-body {
		flex: 1;
		overflow-y: auto;
		overflow-x: hidden;
		padding: 1.5rem 1.5rem 1rem;
		position: relative;
	}

	.flash-content {
		animation-duration: 0.25s;
		animation-timing-function: cubic-bezier(0.22, 1, 0.36, 1);
		animation-fill-mode: both;
	}
	.slide-in-right {
		animation-name: slideInRight;
	}
	.slide-in-left {
		animation-name: slideInLeft;
	}

	@keyframes slideInRight {
		from {
			opacity: 0;
			transform: translateX(40px);
		}
		to {
			opacity: 1;
			transform: translateX(0);
		}
	}
	@keyframes slideInLeft {
		from {
			opacity: 0;
			transform: translateX(-40px);
		}
		to {
			opacity: 1;
			transform: translateX(0);
		}
	}

	.content-section-label {
		font-size: 1.125rem;
		font-weight: 700;
		color: #1e293b;
		line-height: 1.4;
		margin-bottom: 1rem;
		letter-spacing: -0.01em;
	}

	.content-description {
		font-size: 0.9375rem;
		line-height: 1.7;
		color: #475569;
	}
	.content-description :global(p) {
		margin-bottom: 0.5rem;
	}

	.content-annotation {
		position: relative;
		margin-top: 1rem;
		padding: 1rem 1rem 1rem 1.25rem;
		background: #f8fafc;
		border-radius: 0.5rem;
		font-size: 0.875rem;
		line-height: 1.65;
		color: #64748b;
		font-style: italic;
	}
	.annotation-bar {
		position: absolute;
		left: 0;
		top: 0.5rem;
		bottom: 0.5rem;
		width: 3px;
		background: #93c5fd;
		border-radius: 2px;
	}

	/* ── Controls ── */
	.flash-controls {
		flex-shrink: 0;
		padding: 1rem 1.25rem 1.25rem;
		border-top: 1px solid #f1f5f9;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		background: #fafbfc;
	}

	.observation-textarea {
		width: 100%;
		padding: 0.625rem 0.75rem;
		font-size: 0.8125rem;
		line-height: 1.5;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		resize: none;
		background: #fff;
		color: #334155;
		transition:
			border-color 0.15s,
			box-shadow 0.15s;
		font-family: inherit;
	}
	.observation-textarea::placeholder {
		color: #94a3b8;
	}
	.observation-textarea:focus {
		outline: none;
		border-color: #93c5fd;
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}
	.observation-textarea:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* ── Navigation row ── */
	.nav-row {
		display: flex;
		justify-content: space-between;
		gap: 0.75rem;
	}

	.nav-btn {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		border-radius: 0.5rem;
		font-size: 0.8125rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
		border: 1px solid transparent;
	}
	.nav-btn kbd {
		font-size: 0.625rem;
		padding: 0.0625rem 0.3125rem;
		border-radius: 0.1875rem;
		font-family: inherit;
		line-height: 1.4;
	}

	.nav-btn-prev {
		background: #f1f5f9;
		color: #475569;
		border-color: #e2e8f0;
	}
	.nav-btn-prev:hover {
		background: #e2e8f0;
		color: #1e293b;
	}
	.nav-btn-prev kbd {
		background: #e2e8f0;
		color: #94a3b8;
	}

	.nav-btn-next {
		background: #3b82f6;
		color: #fff;
	}
	.nav-btn-next:hover {
		background: #2563eb;
	}
	.nav-btn-next kbd {
		background: rgba(255, 255, 255, 0.2);
		color: rgba(255, 255, 255, 0.8);
	}

	/* ── Jump popover ── */
	.jump-popover {
		position: absolute;
		top: 100%;
		right: 0;
		margin-top: 0.5rem;
		z-index: 20;
		animation: popIn 0.15s cubic-bezier(0.22, 1, 0.36, 1);
	}
	.jump-popover-inner {
		background: #fff;
		border: 1px solid #e2e8f0;
		border-radius: 0.75rem;
		padding: 1rem;
		box-shadow:
			0 4px 6px -1px rgba(0, 0, 0, 0.05),
			0 10px 20px -2px rgba(0, 0, 0, 0.08);
		min-width: 11rem;
	}

	@keyframes popIn {
		from {
			opacity: 0;
			transform: translateY(-4px) scale(0.97);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	.jump-input {
		flex: 1;
		padding: 0.375rem 0.5rem;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		font-size: 0.8125rem;
		width: 100%;
		font-variant-numeric: tabular-nums;
	}
	.jump-input:focus {
		outline: none;
		border-color: #93c5fd;
		box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
	}

	.jump-go-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 2rem;
		height: 2rem;
		border-radius: 0.375rem;
		background: #3b82f6;
		color: #fff;
		border: none;
		cursor: pointer;
		flex-shrink: 0;
		transition: background 0.15s;
	}
	.jump-go-btn:hover {
		background: #2563eb;
	}
</style>
