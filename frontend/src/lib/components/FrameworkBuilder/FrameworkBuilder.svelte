<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { beforeNavigate } from '$app/navigation';
	import {
		createBuilderState,
		setBuilderContext,
		getTranslation,
		withTranslation,
		type Framework,
		type RequirementNode,
		type Question
	} from './builder-state';
	import type { DraftJSON } from './builder-api';
	import {
		localeLabel,
		createCopyHandler,
		createHandleGatedDragHandlers
	} from './builder-utils.svelte';
	import { DEFAULT_FIELD_VISIBILITY } from '$lib/utils/helpers';
	import { locales as supportedLocales } from '$paraglide/runtime';
	import BuilderMinimap from './BuilderMinimap.svelte';
	import BuilderToC from './BuilderToC.svelte';
	import SectionBlock from './SectionBlock.svelte';
	import OutcomesEditor from './OutcomesEditor.svelte';
	import ImplementationGroupsEditor from './ImplementationGroupsEditor.svelte';

	const CONFIGURABLE_FIELDS = [
		'result',
		'status',
		'score',
		'is_scored',
		'documentation_score',
		'observation',
		'answers',
		'evidences',
		'applied_controls',
		'security_exceptions'
	] as const;

	const FIELD_LABELS: Record<string, string> = {
		result: 'Result',
		status: 'Status',
		score: 'Score',
		is_scored: 'Is Scored',
		documentation_score: 'Documentation Score',
		observation: 'Observation',
		answers: 'Answers',
		evidences: 'Evidences',
		applied_controls: 'Applied Controls',
		security_exceptions: 'Security Exceptions'
	};

	function getFieldVisibility(field: string): string {
		return (
			$frameworkStore.field_visibility?.[field] ?? DEFAULT_FIELD_VISIBILITY[field] ?? 'auditor'
		);
	}

	function setFieldVisibility(field: string, value: string) {
		const current = { ...$frameworkStore.field_visibility };
		// If the value matches the code default, remove the override to keep it clean
		if (value === (DEFAULT_FIELD_VISIBILITY[field] ?? 'auditor')) {
			delete current[field];
		} else {
			current[field] = value;
		}
		builder.updateFramework({ field_visibility: current });
	}

	interface Props {
		framework: Framework;
		requirementNodes: RequirementNode[];
		questions: Question[];
		editingDraft?: DraftJSON | null;
	}

	let { framework, requirementNodes, questions, editingDraft = null }: Props = $props();

	const builder = createBuilderState(framework, requirementNodes, questions, editingDraft);
	setBuilderContext(builder);

	const {
		framework: frameworkStore,
		sections: sectionsStore,
		errors: errorsStore,
		saving: savingStore,
		unsaved: unsavedStore,
		unpublished: unpublishedStore,
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
	let showSettings = $state(false);
	let showScoringSettings = $state(false);
	let showScalesEditor = $state(false);
	let newLangCode = $state('');

	// Settings summary for the collapsed state
	let settingsSummary = $derived.by(() => {
		const parts: string[] = [];
		const rules = ($frameworkStore.outcomes_definition ?? []).length;
		const groups = ($frameworkStore.implementation_groups_definition ?? []).length;
		if (rules > 0) parts.push(`${rules} outcome rule${rules > 1 ? 's' : ''}`);
		if (groups > 0) parts.push(`${groups} group${groups > 1 ? 's' : ''}`);
		return parts.length > 0 ? parts.join(', ') : 'No rules or groups configured';
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

	// Drag state for sections
	const sectionDrag = createHandleGatedDragHandlers((from, to) =>
		builder.reorderSections(from, to)
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

	// Warn on SvelteKit navigation — different message depending on save state
	beforeNavigate((navigation) => {
		if (navigation.to?.route?.id === navigation.from?.route?.id) return;
		let hasUnsaved = false;
		let hasUnpublished = false;
		unsavedStore.subscribe((v) => (hasUnsaved = v))();
		unpublishedStore.subscribe((v) => (hasUnpublished = v))();
		if (hasUnsaved) {
			if (!confirm('You have unsaved changes that will be lost. Leave anyway?')) {
				navigation.cancel();
			}
		} else if (hasUnpublished) {
			if (
				!confirm(
					'You have unpublished changes. Your draft is saved and you can resume later. Leave anyway?'
				)
			) {
				navigation.cancel();
			}
		}
	});

	// Ctrl+S / Cmd+S keyboard shortcut
	function handleKeydown(e: KeyboardEvent) {
		if ((e.ctrlKey || e.metaKey) && e.key === 's') {
			e.preventDefault();
			builder.flushDraft();
		}
	}

	// IntersectionObserver for ToC active section tracking
	let observer: IntersectionObserver | null = null;

	onMount(() => {
		window.addEventListener('beforeunload', handleBeforeUnload);
		window.addEventListener('keydown', handleKeydown);

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

		return () => observer?.disconnect();
	});

	// Track only section IDs so the observer reconnects on structural changes, not content edits
	let sectionIds = $derived($sectionsStore.map((s) => s.node.id).join(','));
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

<div class="card !p-0 bg-white shadow-lg overflow-visible">
	<BuilderMinimap frameworkId={framework.id} />

	<div class="flex">
		<BuilderToC />

		<div class="flex-1 min-w-0">
			<div class="{$activeLanguageStore ? 'max-w-5xl' : 'max-w-3xl'} mx-auto px-6 py-8 space-y-8">
				<!-- Framework metadata -->
				<div class="space-y-2" data-framework-metadata>
					{#if $activeLanguageStore}
						<div class="grid grid-cols-2 gap-4">
							<div>
								<span class="text-[10px] text-gray-400 uppercase tracking-wider"
									>{$frameworkStore.locale?.toUpperCase() ?? 'BASE'}</span
								>
								<input
									type="text"
									value={$frameworkStore.name}
									readonly
									class="w-full text-2xl font-bold bg-transparent border-0 border-b-2 border-transparent py-1 text-gray-400 cursor-default"
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
									placeholder="Translate name..."
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
									placeholder="Translate description..."
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
							placeholder="Framework name"
							class="w-full text-2xl font-bold bg-transparent border-0 border-b-2 border-transparent hover:border-gray-300 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors py-1"
							onblur={(e) => {
								builder.updateFramework({ name: e.currentTarget.value });
							}}
						/>
						<textarea
							value={$frameworkStore.description ?? ''}
							placeholder="Framework description (optional)"
							rows="2"
							class="w-full text-sm text-gray-500 bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none py-1"
							onblur={(e) => {
								builder.updateFramework({ description: e.currentTarget.value || null });
							}}
						></textarea>
					{/if}
					{#if $frameworkStore.urn}
						<button
							type="button"
							class="inline-flex items-center gap-1 text-xs font-mono text-gray-300 hover:text-gray-500 transition-colors truncate max-w-full text-left group/urn"
							onclick={() => urnCopy.copy($frameworkStore.urn ?? '')}
						>
							<i
								class="fa-solid {urnCopy.copied ? 'fa-check text-green-500' : 'fa-copy'} text-[9px]"
							></i>
							{#if urnCopy.copied}
								<span class="text-green-500">Copied!</span>
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
				<div class="border border-gray-200 rounded-lg overflow-hidden">
					<button
						type="button"
						class="w-full flex items-center justify-between px-4 py-2.5 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
						onclick={() => (showSettings = !showSettings)}
					>
						<div class="flex items-center gap-2">
							<i
								class="fa-solid {showSettings
									? 'fa-chevron-down'
									: 'fa-chevron-right'} text-[10px] text-gray-400"
							></i>
							<span class="text-xs font-semibold text-gray-600 uppercase tracking-wider"
								>Framework Settings</span
							>
							{#if !showSettings}
								<span class="text-xs text-gray-400">{settingsSummary}</span>
							{/if}
						</div>
						<i class="fa-solid fa-gear text-xs text-gray-400"></i>
					</button>
					{#if showSettings}
						<div class="px-4 py-4 space-y-6 border-t border-gray-200">
							<!-- Annotation -->
							<div>
								<span class="text-xs font-medium text-gray-500 uppercase tracking-wider"
									>Annotation</span
								>
								<textarea
									value={$frameworkStore.annotation ?? ''}
									placeholder="Framework annotation (optional guidance text)"
									rows="2"
									class="mt-1 w-full text-sm text-gray-500 bg-transparent border border-gray-200 rounded-lg px-3 py-2 hover:border-gray-300 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none"
									onblur={(e) => {
										builder.updateFramework({ annotation: e.currentTarget.value || null });
									}}
								></textarea>
							</div>

							<!-- URN namespace -->
							<div>
								<label class="block">
									<span class="text-xs text-gray-500 uppercase tracking-wider font-medium"
										>URN namespace</span
									>
									<input
										type="text"
										value={$frameworkStore.urn_namespace ?? 'custom'}
										placeholder="custom"
										pattern="[a-zA-Z0-9_-]+"
										class="mt-1 w-48 text-sm font-mono border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 {$frameworkStore.editing_version >
										1
											? 'bg-gray-100 text-gray-400 cursor-not-allowed'
											: ''}"
										readonly={$frameworkStore.editing_version > 1}
										onblur={(e) => {
											if ($frameworkStore.editing_version > 1) return;
											const val = e.currentTarget.value.replace(/[^a-zA-Z0-9_-]/g, '') || 'custom';
											builder.updateFramework({ urn_namespace: val });
										}}
									/>
								</label>
								<p class="text-[10px] text-gray-400 mt-0.5">
									Organization in URN prefix (urn:<b>{$frameworkStore.urn_namespace ?? 'custom'}</b
									>:risk:...).
									{#if $frameworkStore.editing_version > 1}
										Locked after first publish.
									{/if}
								</p>
							</div>

							<!-- Scoring settings -->
							<div class="space-y-1.5">
								<button
									type="button"
									class="flex items-center gap-1.5 text-xs font-medium text-gray-500 uppercase tracking-wider hover:text-gray-700 transition-colors"
									onclick={() => (showScoringSettings = !showScoringSettings)}
								>
									<i
										class="fa-solid {showScoringSettings
											? 'fa-chevron-down'
											: 'fa-chevron-right'} text-[9px]"
									></i>
									Scoring settings
								</button>
								{#if showScoringSettings}
									<div class="border border-gray-200 rounded-lg bg-gray-50/50 px-3 py-3 space-y-3">
										<div class="grid grid-cols-3 gap-3">
											<label class="block">
												<span class="text-xs text-gray-500">Min score</span>
												<input
													type="number"
													value={$frameworkStore.min_score}
													class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
													onblur={(e) => {
														builder.updateFramework({
															min_score: parseInt(e.currentTarget.value) || 0
														});
													}}
												/>
											</label>
											<label class="block">
												<span class="text-xs text-gray-500">Max score</span>
												<input
													type="number"
													value={$frameworkStore.max_score}
													class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
													onblur={(e) => {
														builder.updateFramework({
															max_score: parseInt(e.currentTarget.value) || 100
														});
													}}
												/>
											</label>
											<label class="block">
												<span class="text-xs text-gray-500">Aggregation</span>
												<select
													value={getAggregation()}
													class="w-full text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 bg-white"
													onchange={(e) => setAggregation(e.currentTarget.value)}
												>
													<option value="average">Average</option>
													<option value="sum">Sum</option>
												</select>
											</label>
										</div>
										<p class="text-xs text-gray-400">
											<strong>Average</strong> divides total score by number of questions.
											<strong>Sum</strong> adds all scores directly. Use Sum for binary (0/1) scoring.
										</p>

										<!-- Scale entries editor -->
										<div class="border-t border-gray-200 pt-3 space-y-2">
											<button
												type="button"
												class="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors"
												onclick={() => (showScalesEditor = !showScalesEditor)}
											>
												<i
													class="fa-solid {showScalesEditor
														? 'fa-chevron-down'
														: 'fa-chevron-right'} text-[9px]"
												></i>
												Score scale ({scaleEntries.length}
												{scaleEntries.length === 1 ? 'level' : 'levels'})
											</button>
											{#if showScalesEditor}
												<div class="space-y-1.5">
													{#each scaleEntries as entry, idx}
														<div
															class="bg-white border border-gray-200 rounded px-2 py-1.5 space-y-1"
														>
															<div class="flex items-start gap-2">
																<label class="block w-16 shrink-0">
																	<span class="text-[10px] text-gray-400">Score</span>
																	<input
																		type="number"
																		value={entry.score}
																		class="w-full text-sm border border-gray-200 rounded px-1.5 py-0.5 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
																		onblur={(e) => {
																			const entries = [...scaleEntries];
																			entries[idx].score = parseInt(e.currentTarget.value) || 0;
																			setScaleEntries(entries);
																		}}
																	/>
																</label>
																<label class="block flex-1 min-w-0">
																	<span class="text-[10px] text-gray-400">Name</span>
																	<input
																		type="text"
																		value={entry.name}
																		placeholder="e.g. Partial"
																		class="w-full text-sm border border-gray-200 rounded px-1.5 py-0.5 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
																		onblur={(e) => {
																			const entries = [...scaleEntries];
																			entries[idx].name = e.currentTarget.value;
																			setScaleEntries(entries);
																		}}
																	/>
																</label>
																<label class="block flex-1 min-w-0">
																	<span class="text-[10px] text-gray-400">Description</span>
																	<input
																		type="text"
																		value={entry.description}
																		placeholder="Optional"
																		class="w-full text-sm border border-gray-200 rounded px-1.5 py-0.5 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
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
																	class="flex items-start gap-2 pl-16 border-t border-gray-100 pt-1"
																>
																	<label class="block flex-1 min-w-0">
																		<span class="text-[10px] text-blue-500"
																			>{lang.toUpperCase()} Name</span
																		>
																		<input
																			type="text"
																			value={getTranslation(entry.translations, lang, 'name')}
																			placeholder="Translate name..."
																			class="w-full text-sm border border-blue-100 rounded px-1.5 py-0.5 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
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
																			>{lang.toUpperCase()} Description</span
																		>
																		<input
																			type="text"
																			value={getTranslation(
																				entry.translations,
																				lang,
																				'description'
																			)}
																			placeholder="Translate description..."
																			class="w-full text-sm border border-blue-100 rounded px-1.5 py-0.5 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
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
														<i class="fa-solid fa-plus mr-1"></i>Add scale level
													</button>
												</div>
											{/if}
										</div>
									</div>
								{/if}
							</div>

							<!-- Outcome rules -->
							<OutcomesEditor
								outcomes={$frameworkStore.outcomes_definition ?? []}
								onupdate={(rules) => builder.updateFramework({ outcomes_definition: rules })}
								activeLanguage={$activeLanguageStore}
							/>

							<!-- Implementation groups -->
							<ImplementationGroupsEditor
								groups={($frameworkStore.implementation_groups_definition ?? []).map((g) => {
									const rec = g as Record<string, unknown>;
									return {
										ref_id: (rec.ref_id as string) ?? '',
										name: (rec.name as string) ?? '',
										description: (rec.description as string) ?? '',
										default_selected: (rec.default_selected as boolean) ?? false,
										translations:
											(rec.translations as Record<string, Record<string, string>>) ?? null
									};
								})}
								onupdate={(groups) =>
									builder.updateFramework({ implementation_groups_definition: groups })}
								activeLanguage={$activeLanguageStore}
							/>

							<!-- Field Visibility -->
							<div class="space-y-1.5">
								<span class="text-xs font-medium text-gray-500 uppercase tracking-wider"
									>Field Visibility</span
								>
								<p class="text-xs text-gray-400">
									Control which fields are visible to respondents vs auditors.
								</p>
								{#each CONFIGURABLE_FIELDS as field}
									<div class="flex items-center justify-between py-1">
										<span class="text-sm text-gray-600">{FIELD_LABELS[field]}</span>
										<select
											value={getFieldVisibility(field)}
											class="text-xs border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 bg-white"
											onchange={(e) => setFieldVisibility(field, e.currentTarget.value)}
										>
											<option value="everyone">Everyone</option>
											<option value="auditor">Auditor only</option>
											<option value="hidden">Hidden</option>
										</select>
									</div>
								{/each}
							</div>

							<!-- Languages -->
							<div class="space-y-1.5">
								<span class="text-xs font-medium text-gray-500 uppercase tracking-wider"
									>Languages</span
								>
								<p class="text-xs text-gray-400">
									Set the base language and add target languages for translation.
								</p>
								<div class="flex items-center gap-2 py-1">
									<span class="text-sm text-gray-600 w-24">Base language</span>
									<select
										value={$frameworkStore.locale ?? 'en'}
										class="text-sm border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 bg-white"
										onchange={(e) => builder.setBaseLocale(e.currentTarget.value)}
									>
										{#each supportedLocales as code}
											<option value={code}>{localeLabel(code)}</option>
										{/each}
									</select>
								</div>
								<div class="space-y-1">
									<span class="text-xs text-gray-500">Target languages</span>
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
												class="text-xs border border-gray-200 rounded px-2 py-1 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 bg-white"
											>
												<option value="">Add a language...</option>
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
												<i class="fa-solid fa-plus mr-0.5"></i>Add
											</button>
										</div>
									{/if}
								</div>
							</div>
						</div>
					{/if}
				</div>

				<hr class="border-surface-200" />
				<!-- Sections -->
				{#each $sectionsStore as section, sectionIndex (`section-${sectionIndex}-${section.node.id}`)}
					<!-- Add section button between sections -->
					{#if sectionIndex > 0}
						<button
							type="button"
							class="w-full py-2 border-2 border-dashed border-gray-200 rounded-lg text-xs text-gray-300 hover:text-gray-500 hover:border-gray-300 transition-colors opacity-0 hover:opacity-100"
							onclick={() => builder.addSection(sectionIndex - 1)}
						>
							<i class="fa-solid fa-plus mr-1"></i>Insert section
						</button>
					{/if}

					<div
						class:opacity-50={sectionDrag.draggedIndex === sectionIndex}
						draggable="true"
						onmousedown={sectionDrag.recordMousedown}
						ondragstart={(e) => sectionDrag.handleDragStart(e, sectionIndex)}
						ondragover={sectionDrag.handleDragOver}
						ondrop={(e) => sectionDrag.handleDrop(e, sectionIndex)}
						ondragend={sectionDrag.handleDragEnd}
						role="listitem"
					>
						<SectionBlock {section} {sectionIndex} />
					</div>
				{/each}

				<!-- Add section at bottom -->
				<button
					type="button"
					class="w-full py-4 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-400 hover:text-gray-600 hover:border-gray-400 transition-colors"
					onclick={() => builder.addSection()}
				>
					<i class="fa-solid fa-plus mr-1"></i>Add section
				</button>

				<!-- Empty state -->
				{#if $sectionsStore.length === 0}
					<div class="text-center py-16">
						<div
							class="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center"
						>
							<i class="fa-solid fa-layer-group text-2xl text-gray-400"></i>
						</div>
						<h3 class="text-lg font-medium text-gray-600 mb-1">No sections yet</h3>
						<p class="text-sm text-gray-400 mb-4">
							Start building your framework by adding a section.
						</p>
						<p class="text-xs text-gray-400 mb-4 max-w-md mx-auto">
							Sections group your requirements into chapters or domains. Each section becomes a
							top-level category in assessments.
						</p>
						<button
							type="button"
							class="btn preset-filled-primary-500 px-6"
							onclick={() => builder.addSection()}
						>
							<i class="fa-solid fa-plus mr-2"></i>Add first section
						</button>
					</div>
				{/if}

				<!-- Global errors -->
				{#each [...$errorsStore.entries()] as [key, message] (key)}
					{#if key.startsWith('add-') || key.startsWith('reorder-') || key === 'save-draft' || key === 'publish' || key === 'discard'}
						<div class="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-600">
							{message}
						</div>
					{/if}
				{/each}
			</div>
		</div>
	</div>
</div>
