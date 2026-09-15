<script lang="ts">
	import {
		hydrateDraft,
		buildTree,
		nodePassesIgFilter,
		type ImplementationGroup,
		type RequirementNode,
		type BuilderQuestion,
		type BuilderNode,
		type Translations
	} from '$lib/components/FrameworkBuilder/builder-state';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import SplashCard from '$lib/components/FrameworkBuilder/SplashCard.svelte';
	import Question from '$lib/components/Forms/Question.svelte';
	import { pageTitle } from '$lib/utils/stores';

	let { data } = $props();

	// --- State ---

	type NavItem =
		| { type: 'splash'; data: RequirementNode }
		| { type: 'requirement'; data: { node: RequirementNode; questions: BuilderQuestion[] } };

	// $derived, not const: same-route navigation reuses this component with new `data`.
	const draft = $derived(data.draft);
	const editorData = $derived(data.editorData);
	const meta = $derived(editorData.editing_draft.framework_meta);

	$effect(() => {
		$pageTitle = `Preview - ${meta.name || draft.name}`;
	});

	const builderHref = $derived(
		`/experimental/library-builder/${draft.id}/framework?framework_urn=${encodeURIComponent(
			editorData.framework_urn
		)}`
	);

	// The preview renders the saved draft: hydrate it the same way the editor does.
	const rootNodes: BuilderNode[] = $derived.by(() => {
		const { nodes, questions } = hydrateDraft(editorData.editing_draft, editorData.framework_urn);
		return buildTree(nodes, questions);
	});

	const igDefs: ImplementationGroup[] = $derived(
		Array.isArray(meta.implementation_groups_definition)
			? (meta.implementation_groups_definition as ImplementationGroup[])
			: []
	);
	const availableLanguages: string[] = $derived(meta.available_languages ?? []);

	let previewLanguage = $state<string | null>(null);
	let selectedGroups = $state<Set<string>>(new Set());
	let currentIndex = $state(0);
	let answers: Record<string, any> = $state({});

	// --- IG filtering ---

	function toggleGroup(refId: string) {
		const next = new Set(selectedGroups);
		if (next.has(refId)) {
			next.delete(refId);
		} else {
			next.add(refId);
		}
		selectedGroups = next;
	}

	/** Splash screens are presentational and never carry IGs: exempt from the filter. */
	function passesIgFilter(item: NavItem): boolean {
		if (item.type === 'splash') return true;
		return nodePassesIgFilter(item.data.node.implementation_groups, selectedGroups);
	}

	// --- Linearize tree into NavItems ---

	function linearize(tree: BuilderNode[]): NavItem[] {
		const items: NavItem[] = [];

		function walk(nodes: BuilderNode[]) {
			for (const n of nodes) {
				if (n.node.display_mode === 'splash') {
					items.push({ type: 'splash', data: n.node });
				} else if (n.node.assessable) {
					items.push({
						type: 'requirement',
						data: { node: n.node, questions: n.questions }
					});
				}
				if (n.children.length > 0) {
					walk(n.children);
				}
			}
		}

		walk(tree);

		return items;
	}

	// --- Question format adapter ---

	function toQuestionDict(questions: BuilderQuestion[]): Record<string, any> {
		return Object.fromEntries(
			questions.map((bq) => [
				bq.question.urn,
				{
					type: bq.question.type,
					text: t(bq.question.translations, 'text', bq.question.text) || '',
					choices: bq.question.choices.map((c) => ({
						urn: c.urn,
						value: t(c.translations, 'value', c.value) || '',
						description: t(c.translations, 'description', c.description),
						color: c.color,
						add_score: c.add_score,
						compute_result: c.compute_result,
						select_implementation_groups: c.select_implementation_groups
					})),
					annotation: bq.question.annotation,
					depends_on: bq.question.depends_on
				}
			])
		);
	}

	// --- Helpers ---

	/** Resolve an IG ref_id to its display name and tooltip from the framework
	 * definition, applying the preview language like every other field */
	function igChip(refId: string): { label: string; title: string } {
		const def = igDefs.find((d) => d.ref_id === refId);
		const label = t(def?.translations, 'name', def?.name ?? null) || refId;
		return {
			label,
			title: t(def?.translations, 'description', def?.description ?? null) || label
		};
	}

	/** Get display text for a node field, applying translation if preview language is set */
	function t(
		translations: Translations | null | undefined,
		field: string,
		fallback: string | null
	): string {
		if (previewLanguage && translations?.[previewLanguage]?.[field]) {
			return translations[previewLanguage][field];
		}
		return fallback ?? '';
	}

	// --- Derived ---

	let allNavItems = $derived(linearize(rootNodes));
	let navItems = $derived(allNavItems.filter(passesIgFilter));
	let currentItem = $derived(navItems[currentIndex] ?? null);

	function handlePrev() {
		if (currentIndex > 0) currentIndex--;
	}

	function handleNext() {
		if (currentIndex < navItems.length - 1) currentIndex++;
	}

	// Reset index when filter changes
	$effect(() => {
		// Access selectedGroups to track it
		selectedGroups;
		currentIndex = 0;
	});
</script>

<!-- Header bar -->
<div class="sticky top-0 z-40 bg-white border-b border-gray-200 shadow-sm">
	<div class="flex items-center gap-3 py-3 px-6">
		<a
			href={builderHref}
			class="text-sm text-gray-400 hover:text-gray-600 transition-colors shrink-0 flex items-center gap-1.5"
		>
			<i class="fa-solid fa-arrow-left"></i>
			<span>Back to builder</span>
		</a>

		<div class="h-4 w-px bg-gray-200 shrink-0"></div>

		<span
			class="shrink-0 text-xs font-medium px-2 py-0.5 rounded-full bg-purple-100 text-purple-700"
		>
			<i class="fa-solid fa-eye mr-1"></i>Preview
		</span>

		<span class="text-sm text-gray-600 truncate">{meta.name || draft.name}</span>

		{#if availableLanguages.length > 0}
			<div class="ml-auto flex items-center gap-1.5 shrink-0">
				<i class="fa-solid fa-language text-gray-400 text-xs"></i>
				<select
					value={previewLanguage ?? ''}
					class="text-xs border border-gray-200 rounded px-1.5 py-1 focus:border-blue-500 outline-none bg-white cursor-pointer"
					onchange={(e) => (previewLanguage = e.currentTarget.value || null)}
				>
					<option value="">Base language</option>
					{#each availableLanguages as lang}
						<option value={lang}>{lang.toUpperCase()}</option>
					{/each}
				</select>
			</div>
		{/if}
	</div>
</div>

<div class="max-w-3xl mx-auto px-4 py-6 space-y-4">
	<!-- Implementation Group filter -->
	{#if igDefs.length > 0}
		<div class="flex flex-wrap items-center gap-2 p-3 bg-gray-50 rounded-lg border border-gray-200">
			<span class="text-xs font-medium text-gray-500 uppercase tracking-wide mr-1"
				>Filter by implementation group</span
			>
			{#each igDefs as ig}
				{@const active = selectedGroups.has(ig.ref_id)}
				{@const chip = igChip(ig.ref_id)}
				<button
					type="button"
					class="px-3 py-1 rounded-full text-xs font-medium transition-colors border
						{active
						? 'bg-purple-600 text-white border-purple-600'
						: 'bg-white text-gray-600 border-gray-300 hover:bg-gray-100'}"
					onclick={() => toggleGroup(ig.ref_id)}
					title={chip.title}
				>
					{chip.label}
				</button>
			{/each}
			{#if selectedGroups.size > 0}
				<button
					type="button"
					class="text-xs text-gray-400 hover:text-gray-600 ml-1"
					onclick={() => (selectedGroups = new Set())}
				>
					Clear
				</button>
			{/if}
		</div>
	{/if}

	<!-- Card -->
	{#if navItems.length === 0}
		<div class="text-center text-gray-400 py-12">
			<i class="fa-solid fa-folder-open text-3xl mb-3"></i>
			{#if selectedGroups.size > 0}
				<p>No requirements match the selected implementation groups.</p>
				<button
					type="button"
					class="text-sm mt-1 text-purple-600 hover:text-purple-800"
					onclick={() => (selectedGroups = new Set())}
				>
					Clear filter
				</button>
			{:else}
				<p>No items to preview.</p>
				<p class="text-sm mt-1">Add assessable requirements or splash screens in the builder.</p>
			{/if}
		</div>
	{:else if currentItem}
		{#if currentItem.type === 'splash'}
			{@const node = currentItem.data}
			<SplashCard
				name={t(node.translations, 'name', node.name)}
				description={t(node.translations, 'description', node.description)}
				class="card bg-white shadow-md"
			/>
		{:else if currentItem.type === 'requirement'}
			{@const node = currentItem.data.node}
			{@const questions = currentItem.data.questions}
			{@const questionsDict = toQuestionDict(questions)}
			{@const hasQuestions = Object.keys(questionsDict).length > 0}
			<div class="card bg-white shadow-md border-t-[3px] border-t-orange-400 px-6 py-5 space-y-4">
				<h3 class="text-xl font-semibold text-orange-600">
					{node.ref_id ? `${node.ref_id} - ` : ''}{t(node.translations, 'name', node.name) ||
						'Untitled'}
				</h3>
				{#if node.description}
					<div class="card w-full font-light text-lg p-4 preset-tonal-primary">
						<MarkdownRenderer content={t(node.translations, 'description', node.description)} />
					</div>
				{/if}
				{#if node.annotation}
					<div class="card p-4 preset-tonal-secondary text-sm">
						<MarkdownRenderer content={t(node.translations, 'annotation', node.annotation)} />
					</div>
				{/if}
				{#if igDefs.length > 0 && (node.implementation_groups ?? []).length > 0}
					<div class="flex flex-wrap items-center gap-1.5">
						<span class="text-xs text-gray-500 mr-1">Implementation groups:</span>
						{#each node.implementation_groups ?? [] as refId}
							{@const chip = igChip(refId)}
							<span
								class="text-xs px-2 py-0.5 rounded-full border bg-blue-100 border-blue-300 text-blue-700"
								title={chip.title}
							>
								{chip.label}
							</span>
						{/each}
					</div>
				{/if}
				{#if hasQuestions}
					<Question
						questions={questionsDict}
						initialValue={answers}
						field="answers"
						disabled={false}
						onChange={(urn, val) => {
							answers[urn] = val;
							answers = { ...answers };
						}}
					/>
				{/if}
			</div>
		{/if}

		<!-- Navigation -->
		<div class="flex items-center justify-between pt-2">
			<button
				type="button"
				class="px-4 py-2 rounded-lg text-sm font-medium transition-colors
					{currentIndex > 0
					? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
					: 'bg-gray-50 text-gray-300 cursor-not-allowed'}"
				disabled={currentIndex === 0}
				onclick={handlePrev}
			>
				<i class="fa-solid fa-chevron-left mr-1.5"></i>Previous
			</button>

			<span class="text-sm text-gray-500">
				{currentIndex + 1} / {navItems.length}
			</span>

			<button
				type="button"
				class="px-4 py-2 rounded-lg text-sm font-medium transition-colors
					{currentIndex < navItems.length - 1
					? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
					: 'bg-gray-50 text-gray-300 cursor-not-allowed'}"
				disabled={currentIndex === navItems.length - 1}
				onclick={handleNext}
			>
				Next<i class="fa-solid fa-chevron-right ml-1.5"></i>
			</button>
		</div>
	{/if}
</div>
