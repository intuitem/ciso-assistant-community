<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { beforeNavigate } from '$app/navigation';
	import {
		createBuilderState,
		setBuilderContext,
		type Framework,
		type RequirementNode,
		type Question
	} from './builder-state';
	import type { DraftJSON } from './builder-api';
	import BuilderMinimap from './BuilderMinimap.svelte';
	import SectionBlock from './SectionBlock.svelte';
	import OutcomesEditor from './OutcomesEditor.svelte';
	import ImplementationGroupsEditor from './ImplementationGroupsEditor.svelte';

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
		unpublished: unpublishedStore
	} = builder;

	let urnCopied = $state(false);
	let showScoringSettings = $state(false);
	let showScalesEditor = $state(false);

	interface ScaleEntry {
		score: number;
		name: string;
		description: string;
	}

	function getScaleEntries(): ScaleEntry[] {
		const def = $frameworkStore.scores_definition;
		if (!def) return [];
		if (Array.isArray(def)) {
			return def.map((e) => ({
				score: (e as Record<string, unknown>).score as number ?? 0,
				name: (e as Record<string, unknown>).name as string ?? '',
				description: (e as Record<string, unknown>).description as string ?? ''
			}));
		}
		if ('scale' in def && Array.isArray(def.scale)) {
			return (def.scale as Record<string, unknown>[]).map((e) => ({
				score: e.score as number ?? 0,
				name: e.name as string ?? '',
				description: e.description as string ?? ''
			}));
		}
		return [];
	}

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
	let draggedSectionIndex: number | null = $state(null);
	let lastMousedownTarget: EventTarget | null = null;

	function handleSectionDragStart(e: DragEvent, index: number) {
		if (!(lastMousedownTarget as HTMLElement)?.closest('[data-drag-handle]')) {
			e.preventDefault();
			return;
		}
		draggedSectionIndex = index;
	}

	function handleSectionDragOver(e: DragEvent) {
		e.preventDefault();
	}

	function handleSectionDrop(e: DragEvent, dropIndex: number) {
		e.preventDefault();
		if (draggedSectionIndex === null || draggedSectionIndex === dropIndex) return;
		builder.reorderSections(draggedSectionIndex, dropIndex);
		draggedSectionIndex = null;
	}

	function handleSectionDragEnd() {
		draggedSectionIndex = null;
	}

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

	// IntersectionObserver for minimap active section
	onMount(() => {
		window.addEventListener('beforeunload', handleBeforeUnload);
		window.addEventListener('keydown', handleKeydown);

		const observer = new IntersectionObserver(
			(entries) => {
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
		elements.forEach((el) => observer.observe(el));

		return () => observer.disconnect();
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

	<div class="max-w-3xl mx-auto px-6 py-8 space-y-8">
		<!-- Framework metadata -->
		<div class="space-y-2">
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
			<textarea
				value={$frameworkStore.annotation ?? ''}
				placeholder="Framework annotation (optional guidance text)"
				rows="2"
				class="w-full text-sm text-gray-500 bg-transparent border-0 border-b border-transparent hover:border-gray-300 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 transition-colors resize-none py-1"
				onblur={(e) => {
					builder.updateFramework({ annotation: e.currentTarget.value || null });
				}}
			></textarea>
			{#if $frameworkStore.urn}
				<button
					type="button"
					class="inline-flex items-center gap-1 text-xs font-mono text-gray-300 hover:text-gray-500 transition-colors truncate max-w-full text-left group/urn"
					onclick={() => {
						navigator.clipboard.writeText($frameworkStore.urn ?? '');
						urnCopied = true;
						setTimeout(() => (urnCopied = false), 1500);
					}}
				>
					<i class="fa-solid {urnCopied ? 'fa-check text-green-500' : 'fa-copy'} text-[9px]"></i>
					{#if urnCopied}
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

		<!-- Scoring settings -->
		<div class="space-y-1.5">
			<button
				type="button"
				class="flex items-center gap-1.5 text-xs font-medium text-gray-500 uppercase tracking-wider hover:text-gray-700 transition-colors"
				onclick={() => (showScoringSettings = !showScoringSettings)}
			>
				<i
					class="fa-solid {showScoringSettings ? 'fa-chevron-down' : 'fa-chevron-right'} text-[9px]"
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
									builder.updateFramework({ min_score: parseInt(e.currentTarget.value) || 0 });
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
									builder.updateFramework({ max_score: parseInt(e.currentTarget.value) || 100 });
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
							<i class="fa-solid {showScalesEditor ? 'fa-chevron-down' : 'fa-chevron-right'} text-[9px]"></i>
							Score scale ({getScaleEntries().length} {getScaleEntries().length === 1 ? 'level' : 'levels'})
						</button>
						{#if showScalesEditor}
							{@const scaleEntries = getScaleEntries()}
							<div class="space-y-1.5">
								{#each scaleEntries as entry, idx}
									<div class="flex items-start gap-2 bg-white border border-gray-200 rounded px-2 py-1.5">
										<label class="block w-16 shrink-0">
											<span class="text-[10px] text-gray-400">Score</span>
											<input
												type="number"
												value={entry.score}
												class="w-full text-sm border border-gray-200 rounded px-1.5 py-0.5 focus:border-blue-500 outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
												onblur={(e) => {
													const entries = getScaleEntries();
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
													const entries = getScaleEntries();
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
													const entries = getScaleEntries();
													entries[idx].description = e.currentTarget.value;
													setScaleEntries(entries);
												}}
											/>
										</label>
										<button
											type="button"
											class="mt-4 text-gray-300 hover:text-red-500 text-xs transition-colors"
											onclick={() => {
												const entries = getScaleEntries();
												entries.splice(idx, 1);
												setScaleEntries(entries);
											}}
										>
											<i class="fa-solid fa-trash"></i>
										</button>
									</div>
								{/each}
								<button
									type="button"
									class="text-xs text-blue-600 hover:text-blue-700 font-medium"
									onclick={() => {
										const entries = getScaleEntries();
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
		/>

		<!-- Implementation groups -->
		<ImplementationGroupsEditor
			groups={($frameworkStore.implementation_groups_definition ?? []).map((g) => ({
				ref_id: (g as Record<string, string>).ref_id ?? '',
				name: (g as Record<string, string>).name ?? '',
				description: (g as Record<string, string>).description ?? '',
				default_selected: (g as Record<string, unknown>).default_selected as boolean ?? false
			}))}
			onupdate={(groups) => builder.updateFramework({ implementation_groups_definition: groups })}
		/>

		<!-- Sections -->
		{#each $sectionsStore as section, sectionIndex (section.node.id)}
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
				class:opacity-50={draggedSectionIndex === sectionIndex}
				draggable="true"
				onmousedown={(e) => (lastMousedownTarget = e.target)}
				ondragstart={(e) => handleSectionDragStart(e, sectionIndex)}
				ondragover={handleSectionDragOver}
				ondrop={(e) => handleSectionDrop(e, sectionIndex)}
				ondragend={handleSectionDragEnd}
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
				<p class="text-sm text-gray-400 mb-4">Start building your framework by adding a section.</p>
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
