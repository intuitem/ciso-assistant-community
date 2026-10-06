<script lang="ts">
	import { onMount, onDestroy, tick, untrack } from 'svelte';
	import { get } from 'svelte/store';
	import { beforeNavigate } from '$app/navigation';
	import {
		createBuilderState,
		setBuilderContext,
		getTranslation,
		withTranslation,
		extractNodeId,
		type Framework,
		type BuilderNode,
		type RequirementNode,
		type Question
	} from './builder-state';
	import type { DraftJSON } from './builder-api';
	import {
		localeLabel,
		createCopyHandler,
		createHandleGatedDragHandlers,
		REFERENCEABLE_MODELS
	} from './builder-utils.svelte';
	import { locales as supportedLocales } from '$paraglide/runtime';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { installKeyboardHandlers } from './keyboard';
	import {
		createCollapsedStore,
		setCardCollapsedContext,
		setTocCollapsedContext
	} from './collapse-state';
	import KeyboardHelp from './KeyboardHelp.svelte';
	import BuilderMinimap from './BuilderMinimap.svelte';
	import BuilderToC from './BuilderToC.svelte';
	import NodeBlock from './NodeBlock.svelte';
	import AddNodeMenu from './AddNodeMenu.svelte';
	import EmptyState from './EmptyState.svelte';
	import OutcomesEditor from './OutcomesEditor.svelte';
	import OnAcceptEditor from './OnAcceptEditor.svelte';
	import ImplementationGroupsEditor from './ImplementationGroupsEditor.svelte';
	import VisibilityEditor from '$lib/components/ComplianceAssessment/VisibilityEditor.svelte';
	import { initReferentialCatalog } from './referential-catalog';

	interface Props {
		framework: Framework;
		requirementNodes: RequirementNode[];
		questions: Question[];
		editingDraft?: DraftJSON | null;
		/** Adapter path for the _action protocol (defaults to the live-framework builder) */
		apiTarget?: string | null;
		/** Toolbar link overrides for non-live hosts (null preview hides the link) */
		links?: { back?: string; preview?: string | null; exportYaml?: string } | null;
		/** Framework tree (default) or quick form pages */
		mode?: 'framework' | 'quick_form';
	}

	let {
		framework,
		requirementNodes,
		questions,
		editingDraft = null,
		apiTarget = null,
		links = null,
		mode = 'framework'
	}: Props = $props();

	const builder = createBuilderState(framework, requirementNodes, questions, editingDraft, {
		apiTarget: apiTarget ?? undefined,
		mode
	});
	setBuilderContext(builder);
	// Threats / reference controls pickable on nodes; hosts without the
	// reference-catalog action leave the store errored and the UI hidden.
	initReferentialCatalog(builder.apiTarget);

	const cardCollapsed = createCollapsedStore(`fw-builder:${framework.id}:cards:collapsed`);
	setCardCollapsedContext(cardCollapsed);

	const tocCollapsed = createCollapsedStore(`fw-builder:${framework.id}:toc:collapsed`);
	setTocCollapsedContext(tocCollapsed);

	const {
		framework: frameworkStore,
		rootNodes: rootNodesStore,
		errors: errorsStore,
		saving: savingStore,
		unsaved: unsavedStore,
		activeLanguage: activeLanguageStore
	} = builder;

	/** Languages in which this framework has content (base + translated) */
	let frameworkLocales = $derived([
		...new Set([$frameworkStore.locale ?? 'en', ...($frameworkStore.available_languages ?? [])])
	]);

	/** Locales available to add as target languages (not base, not already added) */
	let addableLocales = $derived(
		(supportedLocales as string[]).filter(
			(l) =>
				l !== ($frameworkStore.locale ?? 'en') &&
				!($frameworkStore.available_languages ?? []).includes(l)
		)
	);

	const urnCopy = createCopyHandler();
	let helpOpen = $state(false);
	let showSettings = $state(false);
	// Compliance assessments lock the URN namespace + ref_id inputs once present.
	let lockUrnEdits = $derived($frameworkStore.has_compliance_assessments);
	let showScoringSettings = $state(false);
	let showScalesEditor = $state(false);
	let newLangCode = $state('');

	// Settings summary for the collapsed state
	let settingsSummary = $derived.by(() => {
		const parts: string[] = [];
		const rules = ($frameworkStore.outcomes_definition ?? []).length;
		const groups = ($frameworkStore.implementation_groups_definition ?? []).length;
		if (rules > 0) parts.push(m.builderOutcomeRuleSummary({ count: rules }));
		if (groups > 0) parts.push(m.builderImplementationGroupsSummaryShort({ count: groups }));
		return parts.length > 0 ? parts.join(', ') : m.builderNoRulesOrGroupsConfigured();
	});

	interface ScaleEntry {
		score: number;
		name: string;
		description: string;
		translations?: Record<string, Record<string, string>> | null;
	}

	function getScaleEntries(): ScaleEntry[] {
		const def = $frameworkStore.scores_definition;
		if (!def) return [];
		if (Array.isArray(def)) {
			return def.map((e) => {
				const rec = e as Record<string, unknown>;
				return {
					score: (rec.score as number) ?? 0,
					name: (rec.name as string) ?? '',
					description: (rec.description as string) ?? '',
					translations: (rec.translations as ScaleEntry['translations']) ?? null
				};
			});
		}
		if ('scale' in def && Array.isArray(def.scale)) {
			return (def.scale as Record<string, unknown>[]).map((e) => ({
				score: (e.score as number) ?? 0,
				name: (e.name as string) ?? '',
				description: (e.description as string) ?? '',
				translations: (e.translations as ScaleEntry['translations']) ?? null
			}));
		}
		return [];
	}

	// Cache scale entries so the template reads a single derived instead of calling getScaleEntries() ~11 times
	let scaleEntries = $derived(getScaleEntries());

	function setScaleEntries(entries: ScaleEntry[]) {
		const def = $frameworkStore.scores_definition;
		if (entries.length === 0) {
			// Remove scale from definition, keep other keys
			if (def && typeof def === 'object' && !Array.isArray(def)) {
				const { scale: _, ...rest } = def as Record<string, unknown>;
				builder.updateFramework({
					scores_definition: Object.keys(rest).length > 0 ? rest : null
				});
			} else {
				builder.updateFramework({ scores_definition: null });
			}
			return;
		}
		// Preserve other keys (e.g. aggregation) alongside scale
		const base = def && typeof def === 'object' && !Array.isArray(def) ? { ...def } : {};
		builder.updateFramework({
			scores_definition: { ...base, scale: entries }
		});
	}

	function getAggregation(): string {
		const def = $frameworkStore.scores_definition;
		if (def && typeof def === 'object' && 'aggregation' in def) {
			return (def as Record<string, unknown>).aggregation as string;
		}
		return 'average';
	}

	function setAggregation(value: string) {
		const current = $frameworkStore.scores_definition ?? {};
		if (value === 'average') {
			const { aggregation: _, ...rest } = current as Record<string, unknown>;
			builder.updateFramework({
				scores_definition: Object.keys(rest).length > 0 ? rest : null
			});
		} else {
			builder.updateFramework({
				scores_definition: { ...current, aggregation: value }
			});
		}
	}

	// Single-object reference questions that can name what a response is about.
	// Only saved questions (with a URN) can be picked.
	let subjectCandidates = $derived(
		$rootNodesStore
			.flatMap((bn) => bn.questions.map((bq) => bq.question))
			.filter(
				(q) =>
					(q.type as string) === 'object_reference' &&
					!!q.urn &&
					!(q.config as Record<string, unknown> | null)?.multiple
			)
	);

	let subjectModel = $derived(
		(subjectCandidates.find(
			(q) => q.urn.toLowerCase() === ($frameworkStore.subject_question_urn ?? '').toLowerCase()
		)?.config?.model as string | undefined) ?? null
	);

	// What a new subject question will point at; vendors first, the common case.
	let newSubjectModel = $state<string>('entity');

	/** Add a single-object question at the top of the first page and make it the
	 * subject, so an author never has to know that a subject is a question. */
	function addSubjectQuestion(model: string) {
		if (!get(builder.rootNodes).length) builder.addNode({ parent: null });
		const page = get(builder.rootNodes)[0]?.node;
		if (!page) return;
		const question = builder.addQuestion(page.id, 'object_reference' as Question['type']);
		if (!question) return;
		builder.updateQuestion(question.id, { text: safeTranslate(model), config: { model } });
		const count = get(builder.rootNodes)[0].questions.length;
		if (count > 1) builder.reorderQuestions(page.id, count - 1, 0);
		builder.updateFramework({ subject_question_urn: question.urn });
	}

	// Pages as rules address them (`pages["<node id>"]`), named for the author.
	let rulePages = $derived(
		mode === 'quick_form'
			? $rootNodesStore
					.map((bn) => ({
						id: extractNodeId(bn.node.urn) ?? '',
						label: bn.node.name || bn.node.ref_id || ''
					}))
					.filter((p) => p.id)
			: []
	);

	// A form whose first object question appears is almost always about that
	// object: pick it as subject then. Never over an author's choice, and never
	// on load, so existing forms are left as they are.
	// A subject whose question is gone (deleted, or no longer a single-object
	// reference) would only fail the next save: drop it so it can be re-picked.
	$effect(() => {
		const urns = new Set(subjectCandidates.map((q) => q.urn.toLowerCase()));
		untrack(() => {
			const subject = $frameworkStore.subject_question_urn;
			if (mode === 'quick_form' && subject && !urns.has(subject.toLowerCase())) {
				builder.updateFramework({ subject_question_urn: null });
			}
		});
	});

	let previousCandidateCount = untrack(() => subjectCandidates.length);
	$effect(() => {
		const count = subjectCandidates.length;
		const first = subjectCandidates[0];
		untrack(() => {
			if (
				mode === 'quick_form' &&
				count === 1 &&
				previousCandidateCount === 0 &&
				!$frameworkStore.subject_question_urn
			) {
				builder.updateFramework({ subject_question_urn: first.urn });
			}
			previousCandidateCount = count;
		});
	});

	// Quick forms keep their score settings as {min, max, aggregation} in
	// scores_definition; frameworks use the scale editor above instead.
	function quickFormScore(): { min: number; max: number; aggregation: string } {
		const def = $frameworkStore.scores_definition;
		const rec = def && typeof def === 'object' && !Array.isArray(def) ? def : {};
		return {
			min: typeof rec.min === 'number' ? rec.min : 0,
			max: typeof rec.max === 'number' ? rec.max : 100,
			aggregation: typeof rec.aggregation === 'string' ? rec.aggregation : 'sum'
		};
	}

	function setQuickFormScore(patch: Partial<{ min: number; max: number; aggregation: string }>) {
		const def = $frameworkStore.scores_definition;
		const base = def && typeof def === 'object' && !Array.isArray(def) ? { ...def } : {};
		builder.updateFramework({ scores_definition: { ...quickFormScore(), ...base, ...patch } });
	}

	function collectAllParentIds(tree: BuilderNode[]): string[] {
		const ids: string[] = [];
		function walk(list: BuilderNode[]) {
			for (const n of list) {
				if (n.children.length > 0) {
					ids.push(n.node.id);
					walk(n.children);
				}
			}
		}
		walk(tree);
		return ids;
	}

	// Drag state for root nodes
	const rootDrag = createHandleGatedDragHandlers((from, to) =>
		builder.reorderNodes(null, from, to)
	);

	// --- Navigation guards ---

	// Warn on browser close/refresh if there are unsaved local changes
	function handleBeforeUnload(e: BeforeUnloadEvent) {
		let hasUnsaved = false;
		unsavedStore.subscribe((v) => (hasUnsaved = v))();
		if (hasUnsaved) {
			e.preventDefault();
		}
	}

	// Warn on SvelteKit navigation only for unsaved local edits: once saved,
	// the library-draft document is the persisted state (publishing is a
	// separate, library-level concern).
	beforeNavigate((navigation) => {
		if (navigation.to?.route?.id === navigation.from?.route?.id) return;
		let hasUnsaved = false;
		unsavedStore.subscribe((v) => (hasUnsaved = v))();
		if (hasUnsaved) {
			if (!confirm(m.builderUnsavedChangesNavigation())) {
				navigation.cancel();
			}
		}
	});

	// Most fields commit on `change`, which fires on blur: saving from inside one
	// would send the value from before the edit. Blur commits it, then focus and
	// caret go back so the author keeps typing.
	function commitFocusedField(): () => void {
		const el = document.activeElement;
		if (!(
			el instanceof HTMLInputElement ||
			el instanceof HTMLTextAreaElement ||
			el instanceof HTMLSelectElement
		)) {
			return () => {};
		}
		const caret =
			el instanceof HTMLSelectElement ? null : ([el.selectionStart, el.selectionEnd] as const);
		el.blur();
		return () => {
			el.focus();
			if (caret && caret[0] !== null && el instanceof HTMLTextAreaElement) {
				el.setSelectionRange(caret[0], caret[1]);
			} else if (caret && caret[0] !== null && el instanceof HTMLInputElement) {
				// Some input types (number, color) have no caret to restore.
				try {
					el.setSelectionRange(caret[0], caret[1]);
				} catch {
					/* not a text input */
				}
			}
		};
	}

	// Ctrl+S / Cmd+S keyboard shortcut
	// The fallback is for empty or invalid input only: 0 is a valid bound.
	function intOr(raw: string, fallback: number): number {
		const value = parseInt(raw);
		return Number.isNaN(value) ? fallback : value;
	}

	async function handleKeydown(e: KeyboardEvent) {
		if ((e.ctrlKey || e.metaKey) && e.key === 's') {
			e.preventDefault();
			const refocus = commitFocusedField();
			// After the save: a returned URN map re-renders the fields.
			try {
				await builder.flushDraft();
			} finally {
				refocus();
			}
		}
	}

	// Global ? key — open keyboard cheatsheet
	function handleGlobalKey(e: KeyboardEvent) {
		if (e.key !== '?') return;
		const t = e.target as HTMLElement | null;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
		helpOpen = true;
		e.preventDefault();
	}

	// IntersectionObserver for ToC active section tracking
	let observer: IntersectionObserver | null = null;

	onMount(() => {
		window.addEventListener('beforeunload', handleBeforeUnload);
		window.addEventListener('keydown', handleKeydown);

		const cleanupKeyboard = installKeyboardHandlers(builder);

		observer = new IntersectionObserver(
			(entries) => {
				let isScrolling = false;
				builder.isScrolling.subscribe((v) => (isScrolling = v))();
				if (isScrolling) return;

				for (const entry of entries) {
					if (entry.isIntersecting) {
						const id = (entry.target as HTMLElement).dataset.sectionId;
						if (id) builder.activeSection.set(id);
					}
				}
			},
			{ rootMargin: '-80px 0px -60% 0px', threshold: 0 }
		);

		const elements = document.querySelectorAll('[data-section-id]');
		elements.forEach((el) => observer!.observe(el));

		return () => {
			observer?.disconnect();
			cleanupKeyboard();
		};
	});

	// Track only root node IDs so the observer reconnects on structural changes, not content edits
	let sectionIds = $derived($rootNodesStore.map((s) => s.node.id).join(','));
	let prevSectionIds = '';

	// Re-observe when sections change (e.g., section added/removed)
	$effect(() => {
		const ids = sectionIds;
		if (!observer) return;
		if (ids === prevSectionIds) return;
		prevSectionIds = ids;
		tick().then(() => {
			observer!.disconnect();
			const elements = document.querySelectorAll('[data-section-id]');
			elements.forEach((el) => observer!.observe(el));
		});
	});

	onDestroy(() => {
		if (typeof window !== 'undefined') {
			window.removeEventListener('beforeunload', handleBeforeUnload);
			window.removeEventListener('keydown', handleKeydown);
		}
		builder.destroy();
	});
</script>

<svelte:window onkeydown={handleGlobalKey} />

<div class="card !p-0 bg-surface-50-950 shadow-lg overflow-visible">
	<BuilderMinimap
		frameworkId={framework.id}
		{links}
		onOpenHelp={() => (helpOpen = true)}
		onExpandAllCards={() => cardCollapsed.expandAll()}
		onCollapseAllCards={() => cardCollapsed.collapseAll(collectAllParentIds($rootNodesStore))}
	/>

	<div class="flex">
		<BuilderToC />

		<div class="flex-1 min-w-0">
			<div class="max-w-5xl mx-auto px-6 py-8 space-y-8">
				{#if $errorsStore.has('save-draft')}
					<div
						class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700 whitespace-pre-line"
						role="alert"
						data-testid="builder-save-error"
					>
						<i class="fa-solid fa-triangle-exclamation mr-1"></i>{$errorsStore.get('save-draft')}
					</div>
				{/if}
				<!-- Framework metadata -->
				<div class="space-y-2" data-framework-metadata>
					{#if $activeLanguageStore}
						<div class="grid grid-cols-2 gap-4">
							<div>
								<span class="text-[10px] text-surface-500 uppercase tracking-wider"
									>{$frameworkStore.locale?.toUpperCase() ?? 'BASE'}</span
								>
								<input
									type="text"
									value={$frameworkStore.name}
									readonly
									class="w-full text-2xl font-bold bg-transparent border-0 border-b-2 border-transparent py-1 text-surface-500 cursor-default"
								/>
								<textarea
									value={$frameworkStore.description ?? ''}
									readonly
									rows="2"
									class="w-full text-sm text-gray-300 bg-transparent border-0 border-b border-transparent resize-none py-1 cursor-default"
								></textarea>
							</div>
							<div>
								<span class="text-[10px] text-blue-600 uppercase tracking-wider font-medium"
									>{$activeLanguageStore.toUpperCase()}</span
								>
								<input
									type="text"
									value={getTranslation($frameworkStore.translations, $activeLanguageStore, 'name')}
									placeholder={m.builderTranslateName()}
									class="w-full text-2xl font-bold bg-transparent border-0 border-b-2 border-transparent hover:border-blue-300 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors py-1"
									onblur={(e) => {
										builder.updateFramework({
											translations: withTranslation(
												$frameworkStore.translations,
												$activeLanguageStore!,
												'name',
												e.currentTarget.value
											)
										});
									}}
								/>
								<textarea
									value={getTranslation(
										$frameworkStore.translations,
										$activeLanguageStore,
										'description'
									)}
									placeholder={m.builderTranslateDescription()}
									rows="2"
									class="w-full text-sm bg-transparent border-0 border-b border-transparent hover:border-blue-300 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none py-1"
									onblur={(e) => {
										builder.updateFramework({
											translations: withTranslation(
												$frameworkStore.translations,
												$activeLanguageStore!,
												'description',
												e.currentTarget.value
											)
										});
									}}
								></textarea>
							</div>
						</div>
					{:else}
						<input
							type="text"
							value={$frameworkStore.name}
							placeholder={m.builderFrameworkNamePlaceholder()}
							class="w-full text-2xl font-bold bg-transparent border-0 border-b-2 border-transparent hover:border-surface-300-700 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors py-1"
							onblur={(e) => {
								builder.updateFramework({ name: e.currentTarget.value });
							}}
						/>
						<textarea
							value={$frameworkStore.description ?? ''}
							placeholder={mode === 'quick_form'
								? m.builderFormDescriptionPlaceholder()
								: m.builderFrameworkDescriptionPlaceholder()}
							rows="2"
							class="w-full text-sm text-surface-600-400 bg-transparent border-0 border-b border-transparent hover:border-surface-300-700 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none py-1"
							onblur={(e) => {
								builder.updateFramework({ description: e.currentTarget.value || null });
							}}
						></textarea>
					{/if}
					{#if $frameworkStore.urn}
						<button
							type="button"
							class="inline-flex items-center gap-1 text-xs font-mono text-gray-300 hover:text-surface-600-400 transition-colors truncate max-w-full text-left group/urn"
							onclick={() => urnCopy.copy($frameworkStore.urn ?? '')}
						>
							<i
								class="fa-solid {urnCopy.copied ? 'fa-check text-green-500' : 'fa-copy'} text-[9px]"
							></i>
							{#if urnCopy.copied}
								<span class="text-green-500">{m.copied()}</span>
							{:else}
								{$frameworkStore.urn}
							{/if}
						</button>
					{/if}
					{#if $errorsStore.has('framework')}
						<p class="text-xs text-red-600">{$errorsStore.get('framework')}</p>
					{/if}
				</div>

				<!-- Framework Settings (collapsed by default) -->
				<div class="border border-surface-200-800 rounded-lg overflow-hidden">
					<button
						type="button"
						class="w-full flex items-center justify-between px-4 py-2.5 bg-surface-50-950 hover:bg-surface-100-900 transition-colors text-left"
						onclick={() => (showSettings = !showSettings)}
					>
						<div class="flex items-center gap-2">
							<i
								class="fa-solid {showSettings
									? 'fa-chevron-down'
									: 'fa-chevron-right'} text-[10px] text-surface-500"
							></i>
							<span class="text-xs font-semibold text-surface-600-400 uppercase tracking-wider"
								>{mode === 'quick_form'
									? m.builderFormSettings()
									: m.builderFrameworkSettings()}</span
							>
							{#if !showSettings}
								<span class="text-xs text-surface-500">{settingsSummary}</span>
							{/if}
						</div>
						<i class="fa-solid fa-gear text-xs text-surface-500"></i>
					</button>
					{#if showSettings}
						<div class="px-4 py-4 space-y-6 border-t border-surface-200-800">
							<!-- Annotation -->
							<div>
								<span class="text-xs font-medium text-surface-600-400 uppercase tracking-wider"
									>{m.annotation()}</span
								>
								<textarea
									value={$frameworkStore.annotation ?? ''}
									placeholder={mode === 'quick_form'
										? m.builderFormAnnotationPlaceholder()
										: m.builderFrameworkAnnotationPlaceholder()}
									rows="2"
									class="mt-1 w-full text-sm text-surface-600-400 bg-transparent border border-surface-200-800 rounded-lg px-3 py-2 hover:border-surface-300-700 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none"
									onblur={(e) => {
										builder.updateFramework({ annotation: e.currentTarget.value || null });
									}}
								></textarea>
							</div>

							<!-- URN namespace + ref_id -->
							<div>
								<div class="flex gap-3">
									<label class="block">
										<span class="text-xs text-surface-600-400 uppercase tracking-wider font-medium"
											>{m.builderUrnNamespace()}</span
										>
										<input
											type="text"
											value={$frameworkStore.urn_namespace ?? 'custom'}
											placeholder="custom"
											pattern="[a-zA-Z0-9_-]+"
											class="mt-1 w-48 text-sm font-mono border border-surface-200-800 rounded bg-surface-100-900 px-2 py-1 text-surface-950-50 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 {lockUrnEdits
												? 'text-surface-500 cursor-not-allowed'
												: ''}"
											readonly={lockUrnEdits}
											onblur={(e) => {
												if (lockUrnEdits) return;
												const val =
													e.currentTarget.value.replace(/[^a-zA-Z0-9_-]/g, '') || 'custom';
												builder.updateFramework({ urn_namespace: val });
											}}
										/>
									</label>
									<label class="block">
										<span class="text-xs text-surface-600-400 uppercase tracking-wider font-medium"
											>{m.frameworkRefId()}</span
										>
										<input
											type="text"
											value={$frameworkStore.ref_id ?? ''}
											placeholder="my-framework"
											pattern="[a-zA-Z0-9_-]+"
											class="mt-1 w-48 text-sm font-mono border border-surface-200-800 rounded bg-surface-100-900 px-2 py-1 text-surface-950-50 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 {lockUrnEdits
												? 'text-surface-500 cursor-not-allowed'
												: ''}"
											readonly={lockUrnEdits}
											onblur={(e) => {
												if (lockUrnEdits) return;
												const val = e.currentTarget.value.replace(/[^a-zA-Z0-9_-]/g, '');
												builder.updateFramework({ ref_id: val || null });
											}}
										/>
									</label>
								</div>
								<p class="text-[10px] text-surface-500 mt-0.5">
									{m.urnPreview()}
									<code
										>urn:{$frameworkStore.urn_namespace ?? 'custom'}:risk:{mode === 'quick_form'
											? 'quick_form'
											: 'framework'}:{$frameworkStore.ref_id || '…'}</code
									>
									{#if lockUrnEdits}
										{mode === 'quick_form'
											? m.urnLockedQuickFormResponses()
											: m.urnLockedComplianceAssessment()}
									{/if}
								</p>
							</div>

							{#if mode === 'quick_form'}
								<div
									class="border border-surface-200-800 rounded-lg bg-surface-50-950/50 px-3 py-3 space-y-2"
									data-testid="quick-form-score-settings"
								>
									<p class="text-xs font-medium text-surface-600-400 uppercase tracking-wider">
										{m.builderQuickFormScore()}
									</p>
									<div class="grid grid-cols-3 gap-3">
										<label class="block">
											<span class="text-xs text-surface-600-400">{m.aggregation()}</span>
											<select
												value={quickFormScore().aggregation}
												class="w-full text-sm border border-surface-200-800 rounded px-2 py-1 bg-surface-50-950"
												onchange={(e) => setQuickFormScore({ aggregation: e.currentTarget.value })}
											>
												<option value="sum">{m.builderScoreSumOfQuestions()}</option>
												<option value="mean">{m.builderScoreMeanOfQuestions()}</option>
												<option value="pages_sum">{m.builderScoreSumOfPages()}</option>
												<option value="pages_mean">{m.builderScoreMeanOfPages()}</option>
											</select>
										</label>
										<label class="block">
											<span class="text-xs text-surface-600-400">{m.minScore()}</span>
											<input
												type="number"
												value={quickFormScore().min}
												class="input w-full text-sm border border-surface-200-800 rounded px-2 py-1"
												onblur={(e) => setQuickFormScore({ min: intOr(e.currentTarget.value, 0) })}
											/>
										</label>
										<label class="block">
											<span class="text-xs text-surface-600-400">{m.maxScore()}</span>
											<input
												type="number"
												value={quickFormScore().max}
												class="input w-full text-sm border border-surface-200-800 rounded px-2 py-1"
												onblur={(e) =>
													setQuickFormScore({ max: intOr(e.currentTarget.value, 100) })}
											/>
										</label>
									</div>
									<p class="text-xs text-surface-500">{m.builderQuickFormScoreHint()}</p>
								</div>
								<label class="block" data-testid="subject-question">
									<span class="text-xs font-medium text-surface-600-400 uppercase tracking-wider"
										>{m.builderSubjectQuestion()}</span
									>
									<select
										value={$frameworkStore.subject_question_urn ?? ''}
										class="w-full text-sm border border-surface-200-800 rounded px-2 py-1 bg-surface-50-950"
										onchange={(e) =>
											builder.updateFramework({
												subject_question_urn: e.currentTarget.value || null
											})}
									>
										<option value="">{m.builderNoSubjectQuestion()}</option>
										{#each subjectCandidates as question (question.urn)}
											<option value={question.urn}
												>{question.text || question.ref_id || question.urn} ({safeTranslate(
													String(question.config?.model ?? '')
												)})</option
											>
										{/each}
									</select>
									<span class="text-xs text-surface-500">{m.builderSubjectQuestionHint()}</span>
									{#if !subjectCandidates.length}
										<span
											class="mt-1.5 flex flex-wrap items-center gap-2"
											data-testid="add-subject"
										>
											<select
												class="text-xs border border-surface-200-800 rounded px-2 py-1 bg-surface-50-950"
												aria-label={m.builderReferenceModel()}
												bind:value={newSubjectModel}
											>
												{#each REFERENCEABLE_MODELS as model}
													<option value={model}>{safeTranslate(model)}</option>
												{/each}
											</select>
											<button
												type="button"
												class="btn btn-sm preset-tonal-primary"
												onclick={() => addSubjectQuestion(newSubjectModel)}
												data-testid="add-subject-question"
											>
												<i class="fa-solid fa-plus mr-1"></i>{m.builderAddSubjectQuestion()}
											</button>
										</span>
									{/if}
								</label>
							{/if}

							{#if mode === 'framework'}
								<!-- Scoring settings -->
								<div class="space-y-1.5">
									<button
										type="button"
										class="flex items-center gap-1.5 text-xs font-medium text-surface-600-400 uppercase tracking-wider hover:text-surface-700-300 transition-colors"
										onclick={() => (showScoringSettings = !showScoringSettings)}
									>
										<i
											class="fa-solid {showScoringSettings
												? 'fa-chevron-down'
												: 'fa-chevron-right'} text-[9px]"
										></i>
										{m.builderScoringSettings()}
									</button>
									{#if showScoringSettings}
										<div
											class="border border-surface-200-800 rounded-lg bg-surface-50-950/50 px-3 py-3 space-y-3"
										>
											<div class="grid grid-cols-3 gap-3">
												<label class="block">
													<span class="text-xs text-surface-600-400">{m.minScore()}</span>
													<input
														type="number"
														value={$frameworkStore.min_score}
														class="input w-full text-sm border border-surface-200-800 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
														onblur={(e) => {
															builder.updateFramework({
																min_score: parseInt(e.currentTarget.value) || 0
															});
														}}
													/>
												</label>
												<label class="block">
													<span class="text-xs text-surface-600-400">{m.maxScore()}</span>
													<input
														type="number"
														value={$frameworkStore.max_score}
														class="input w-full text-sm border border-surface-200-800 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
														onblur={(e) => {
															builder.updateFramework({
																max_score: parseInt(e.currentTarget.value) || 100
															});
														}}
													/>
												</label>
												<label class="block">
													<span class="text-xs text-surface-600-400">{m.aggregation()}</span>
													<select
														value={getAggregation()}
														class="w-full text-sm border border-surface-200-800 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 bg-surface-50-950"
														onchange={(e) => setAggregation(e.currentTarget.value)}
													>
														<option value="average">{m.average()}</option>
														<option value="sum">{m.sum()}</option>
													</select>
												</label>
											</div>
											<p class="text-xs text-surface-500">
												{m.builderAggregationHint()}
											</p>

											<!-- Scale entries editor -->
											<div class="border-t border-surface-200-800 pt-3 space-y-2">
												<button
													type="button"
													class="flex items-center gap-1.5 text-xs font-medium text-surface-600-400 hover:text-surface-700-300 transition-colors"
													onclick={() => (showScalesEditor = !showScalesEditor)}
												>
													<i
														class="fa-solid {showScalesEditor
															? 'fa-chevron-down'
															: 'fa-chevron-right'} text-[9px]"
													></i>
													{m.builderScoreScale()} ({m.builderScaleLevel({
														count: scaleEntries.length
													})})
												</button>
												{#if showScalesEditor}
													<div class="space-y-1.5">
														{#each scaleEntries as entry, idx}
															<div
																class="bg-surface-50-950 border border-surface-200-800 rounded px-2 py-1.5 space-y-1"
															>
																<div class="flex items-start gap-2">
																	<label class="block w-16 shrink-0">
																		<span class="text-[10px] text-surface-500">{m.score()}</span>
																		<input
																			type="number"
																			value={entry.score}
																			class="input w-full text-sm border border-surface-200-800 rounded px-1.5 py-0.5 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
																			onblur={(e) => {
																				const entries = [...scaleEntries];
																				entries[idx].score = parseInt(e.currentTarget.value) || 0;
																				setScaleEntries(entries);
																			}}
																		/>
																	</label>
																	<label class="block flex-1 min-w-0">
																		<span class="text-[10px] text-surface-500">{m.name()}</span>
																		<input
																			type="text"
																			value={entry.name}
																			placeholder={m.builderScaleNamePlaceholder()}
																			class="input w-full text-sm border border-surface-200-800 rounded px-1.5 py-0.5 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
																			onblur={(e) => {
																				const entries = [...scaleEntries];
																				entries[idx].name = e.currentTarget.value;
																				setScaleEntries(entries);
																			}}
																		/>
																	</label>
																	<label class="block flex-1 min-w-0">
																		<span class="text-[10px] text-surface-500"
																			>{m.description()}</span
																		>
																		<input
																			type="text"
																			value={entry.description}
																			placeholder={m.builderScaleDescriptionPlaceholder()}
																			class="input w-full text-sm border border-surface-200-800 rounded px-1.5 py-0.5 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
																			onblur={(e) => {
																				const entries = [...scaleEntries];
																				entries[idx].description = e.currentTarget.value;
																				setScaleEntries(entries);
																			}}
																		/>
																	</label>
																	<button
																		type="button"
																		class="mt-4 text-gray-300 hover:text-red-500 text-xs transition-colors"
																		onclick={() => {
																			const entries = [...scaleEntries];
																			entries.splice(idx, 1);
																			setScaleEntries(entries);
																		}}
																	>
																		<i class="fa-solid fa-trash"></i>
																	</button>
																</div>
																{#if $activeLanguageStore}
																	{@const lang = $activeLanguageStore}
																	<div
																		class="flex items-start gap-2 pl-16 border-t border-surface-100-900 pt-1"
																	>
																		<label class="block flex-1 min-w-0">
																			<span class="text-[10px] text-blue-500"
																				>{m.builderScaleNameTranslate({
																					lang: lang.toUpperCase()
																				})}</span
																			>
																			<input
																				type="text"
																				value={getTranslation(entry.translations, lang, 'name')}
																				placeholder={m.builderTranslateName()}
																				class="input w-full text-sm border border-blue-100 dark:border-blue-900/40 rounded px-1.5 py-0.5 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
																				onblur={(e) => {
																					const entries = [...scaleEntries];
																					entries[idx].translations = withTranslation(
																						entries[idx].translations,
																						lang,
																						'name',
																						e.currentTarget.value
																					);
																					setScaleEntries(entries);
																				}}
																			/>
																		</label>
																		<label class="block flex-1 min-w-0">
																			<span class="text-[10px] text-blue-500"
																				>{m.builderScaleDescriptionTranslate({
																					lang: lang.toUpperCase()
																				})}</span
																			>
																			<input
																				type="text"
																				value={getTranslation(
																					entry.translations,
																					lang,
																					'description'
																				)}
																				placeholder={m.builderTranslateDescription()}
																				class="input w-full text-sm border border-blue-100 dark:border-blue-900/40 rounded px-1.5 py-0.5 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
																				onblur={(e) => {
																					const entries = [...scaleEntries];
																					entries[idx].translations = withTranslation(
																						entries[idx].translations,
																						lang,
																						'description',
																						e.currentTarget.value
																					);
																					setScaleEntries(entries);
																				}}
																			/>
																		</label>
																	</div>
																{/if}
															</div>
														{/each}
														<button
															type="button"
															class="text-xs text-blue-600 hover:text-blue-700 font-medium"
															onclick={() => {
																const entries = [...scaleEntries];
																entries.push({ score: 0, name: '', description: '' });
																setScaleEntries(entries);
															}}
														>
															<i class="fa-solid fa-plus mr-1"></i>{m.builderAddScaleLevel()}
														</button>
													</div>
												{/if}
											</div>
										</div>
									{/if}
								</div>
							{/if}
							<!-- Outcome rules -->
							<OutcomesEditor
								outcomes={$frameworkStore.outcomes_definition ?? []}
								onupdate={(rules) => builder.updateFramework({ outcomes_definition: rules })}
								activeLanguage={$activeLanguageStore}
								{mode}
								pages={rulePages}
							/>

							{#if mode === 'quick_form'}
								<OnAcceptEditor
									value={($frameworkStore.on_accept ?? []) as any[]}
									rules={$frameworkStore.outcomes_definition ?? []}
									{subjectModel}
									onaddvendorsubject={() => addSubjectQuestion('entity')}
									onupdate={(on_accept) => builder.updateFramework({ on_accept })}
								/>
							{/if}

							{#if mode === 'framework'}
								<!-- Implementation groups -->
								<ImplementationGroupsEditor
									groups={($frameworkStore.implementation_groups_definition ?? []).map((g) => {
										const rec = g as Record<string, unknown>;
										return {
											ref_id: (rec.ref_id as string) ?? '',
											name: (rec.name as string) ?? '',
											description: (rec.description as string) ?? '',
											default_selected: (rec.default_selected as boolean) ?? false,
											// Not edited here, but kept: audits of the group are proposed it.
											target_score: (rec.target_score as number | null | undefined) ?? undefined,
											translations:
												(rec.translations as Record<string, Record<string, string>>) ?? null
										};
									})}
									onupdate={(groups) =>
										builder.updateFramework({ implementation_groups_definition: groups })}
									activeLanguage={$activeLanguageStore}
								/>

								<!-- Field Visibility -->
								<VisibilityEditor
									value={$frameworkStore.field_visibility}
									onChange={(next) => builder.updateFramework({ field_visibility: next })}
								/>
							{/if}
							<!-- Languages -->
							<div class="space-y-1.5">
								<span class="text-xs font-medium text-surface-600-400 uppercase tracking-wider"
									>{m.builderLanguagesSection()}</span
								>
								<p class="text-xs text-surface-500">
									{m.builderLanguagesHint()}
								</p>
								<div class="flex items-center gap-2 py-1">
									<span class="text-sm text-surface-600-400 w-24">{m.builderBaseLanguage()}</span>
									<select
										value={$frameworkStore.locale ?? 'en'}
										class="text-sm border border-surface-200-800 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 bg-surface-50-950"
										onchange={(e) => builder.setBaseLocale(e.currentTarget.value)}
									>
										{#each supportedLocales as code}
											<option value={code}>{localeLabel(code)}</option>
										{/each}
									</select>
								</div>
								<div class="space-y-1">
									<span class="text-xs text-surface-600-400">{m.builderTargetLanguages()}</span>
									<div class="flex flex-wrap gap-1.5">
										{#each $frameworkStore.available_languages ?? [] as lang}
											<span
												class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200"
											>
												{localeLabel(lang)}
												<button
													type="button"
													class="text-blue-400 hover:text-red-500 transition-colors"
													onclick={() => builder.removeLanguage(lang)}
												>
													<i class="fa-solid fa-times text-[9px]"></i>
												</button>
											</span>
										{/each}
									</div>
									{#if addableLocales.length > 0}
										<div class="flex items-center gap-1.5 mt-1">
											<select
												bind:value={newLangCode}
												class="text-xs border border-surface-200-800 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 bg-surface-50-950"
											>
												<option value="">{m.builderAddLanguagePlaceholder()}</option>
												{#each addableLocales as code}
													<option value={code}>{localeLabel(code)}</option>
												{/each}
											</select>
											<button
												type="button"
												class="text-xs text-blue-600 hover:text-blue-700 font-medium disabled:opacity-40"
												disabled={!newLangCode}
												onclick={() => {
													builder.addLanguage(newLangCode);
													newLangCode = '';
												}}
											>
												<i class="fa-solid fa-plus mr-0.5"></i>{m.builderAdd()}
											</button>
										</div>
									{/if}
								</div>
							</div>
						</div>
					{/if}
				</div>

				<hr class="border-surface-200" />
				<!-- Root nodes -->
				{#if $rootNodesStore.length === 0}
					<EmptyState />
				{:else}
					{#each $rootNodesStore as bn, i (bn.node.id)}
						<div
							class:opacity-50={rootDrag.draggedIndex === i}
							draggable="true"
							onmousedown={rootDrag.recordMousedown}
							ondragstart={(e) => rootDrag.handleDragStart(e, i)}
							ondragover={rootDrag.handleDragOver}
							ondrop={(e) => rootDrag.handleDrop(e, i)}
							ondragend={rootDrag.handleDragEnd}
							role="listitem"
						>
							<NodeBlock node={bn} parentId={null} indexWithinParent={i} />
						</div>
					{/each}

					{#if mode === 'quick_form'}
						<button
							type="button"
							class="w-full py-4 border-2 border-dashed border-surface-200-800 rounded-lg text-sm text-surface-500 hover:text-surface-600-400 hover:border-surface-300-700 transition-colors"
							onclick={() => builder.addNode({ parent: null, preset: 'requirement' })}
						>
							<i class="fa-solid fa-plus mr-1"></i>{m.builderAddPage()}
						</button>
					{:else}
						<AddNodeMenu
							parent={null}
							triggerLabel={m.builderAddTopLevelNode()}
							triggerClass="w-full py-4 border-2 border-dashed border-surface-200-800 rounded-lg text-sm text-surface-500 hover:text-surface-600-400 hover:border-surface-300-700 transition-colors"
						/>
					{/if}
				{/if}

				<!-- Global errors -->
				{#each [...$errorsStore.entries()] as [key, message] (key)}
					{#if key.startsWith('add-') || key.startsWith('reorder-')}
						<div class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-600">
							{message}
						</div>
					{/if}
				{/each}
			</div>
		</div>
	</div>
</div>

<KeyboardHelp bind:open={helpOpen} onClose={() => (helpOpen = false)} />
