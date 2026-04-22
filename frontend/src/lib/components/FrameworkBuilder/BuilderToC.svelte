<script lang="ts">
	import { onMount } from 'svelte';
	import { getBuilderContext } from './builder-state';
	import { getTocCollapsedContext } from './collapse-state';

	import type { BuilderNode } from './builder-state';

	const builder = getBuilderContext();
	const {
		rootNodes: rootNodesStore,
		activeSection: activeSectionStore,
		isScrolling: isScrollingStore,
		activeLanguage: activeLanguageStore
	} = builder;

	const tocCollapsed = getTocCollapsedContext();

	let collapsed = $state(false);
	let searchQuery = $state('');
	let focusedIndex = $state(-1);
	let searchInput = $state<HTMLInputElement>();
	let navigationButtons = $state<HTMLButtonElement[]>([]);
	let topOffset = $state(0);

	let tocCollapsedSet = $state(new Set<string>());
	$effect(() => {
		const unsub = tocCollapsed.subscribe((s) => (tocCollapsedSet = s));
		return unsub;
	});

	const FRAMEWORK_ID = '__framework__';

	interface TocEntry {
		node: BuilderNode;
		depth: number;
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

	function flattenTree(tree: BuilderNode[], depth = 0): TocEntry[] {
		const out: TocEntry[] = [];
		for (const n of tree) {
			out.push({ node: n, depth });
			if (n.children.length > 0 && !tocCollapsedSet.has(n.node.id)) {
				out.push(...flattenTree(n.children, depth + 1));
			}
		}
		return out;
	}

	// allEntries references both $rootNodesStore and tocCollapsedSet — flattenTree reads
	// tocCollapsedSet directly so Svelte tracks it as a dependency automatically.
	let allEntries = $derived(flattenTree($rootNodesStore));

	let filteredNodes = $derived(
		searchQuery
			? allEntries.filter((e) => {
					const label = e.node.node.ref_id || e.node.node.name || '';
					return label.toLowerCase().includes(searchQuery.toLowerCase());
				})
			: allEntries
	);

	$effect(() => {
		if (filteredNodes.length > 0 && focusedIndex >= filteredNodes.length) {
			focusedIndex = 0;
		}
	});

	onMount(() => {
		// Measure toolbar height for sticky offset
		const appBar = document.querySelector('[data-scope="app-bar"]');
		if (appBar) {
			topOffset = appBar.getBoundingClientRect().height;
		}

		// Auto-collapse below lg breakpoint
		const mq = window.matchMedia('(max-width: 1023px)');
		const handler = (e: MediaQueryListEvent) => {
			if (e.matches) collapsed = true;
		};
		mq.addEventListener('change', handler);
		if (mq.matches) collapsed = true;

		return () => mq.removeEventListener('change', handler);
	});

	/** Check if a node has any untranslated items for the active language */
	function hasUntranslated(nodes: BuilderNode[], lang: string): boolean {
		for (const r of nodes) {
			if (r.node.name && !r.node.translations?.[lang]?.name) return true;
			for (const bq of r.questions) {
				if (bq.question.text && !bq.question.translations?.[lang]?.text) return true;
				for (const c of bq.question.choices) {
					if (c.value && !c.translations?.[lang]?.value) return true;
				}
			}
			if (r.children.length > 0 && hasUntranslated(r.children, lang)) return true;
		}
		return false;
	}

	/** Count all descendants (not including self) */
	function countDescendants(nodes: BuilderNode[]): number {
		let count = 0;
		for (const n of nodes) {
			count += n.children.length;
			if (n.children.length > 0) count += countDescendants(n.children);
		}
		return count;
	}

	function scrollToNode(nodeId: string) {
		isScrollingStore.set(true);
		activeSectionStore.set(nodeId);

		if (nodeId === FRAMEWORK_ID) {
			const container = document.querySelector('[data-framework-metadata]');
			if (container) {
				container.scrollIntoView({ behavior: 'smooth', block: 'start' });
			}
		} else {
			const el = document.querySelector(`[data-section-id="${nodeId}"]`);
			if (el) {
				el.scrollIntoView({ behavior: 'smooth', block: 'start' });
			}
		}

		setTimeout(() => isScrollingStore.set(false), 1000);
	}

	function toggleCollapse() {
		collapsed = !collapsed;
		if (!collapsed) {
			setTimeout(() => searchInput?.focus(), 100);
		} else {
			searchQuery = '';
			focusedIndex = -1;
		}
	}

	function clearSearch() {
		searchQuery = '';
		focusedIndex = -1;
		searchInput?.focus();
	}

	function focusItem(index: number) {
		if (index >= 0 && index < filteredNodes.length && navigationButtons[index]) {
			focusedIndex = index;
			navigationButtons[index].focus();
			navigationButtons[index].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
		}
	}

	function handleSearchKeydown(event: KeyboardEvent) {
		switch (event.key) {
			case 'Escape':
				event.preventDefault();
				if (searchQuery) {
					clearSearch();
				} else {
					collapsed = true;
				}
				break;
			case 'ArrowDown':
				event.preventDefault();
				if (filteredNodes.length > 0) {
					focusItem(focusedIndex < 0 ? 0 : Math.min(focusedIndex + 1, filteredNodes.length - 1));
				}
				break;
			case 'ArrowUp':
				event.preventDefault();
				if (focusedIndex > 0) {
					focusItem(focusedIndex - 1);
				} else if (focusedIndex === 0) {
					focusedIndex = -1;
					searchInput?.focus();
				}
				break;
			case 'Enter':
				event.preventDefault();
				if (focusedIndex >= 0) {
					scrollToNode(filteredNodes[focusedIndex].node.node.id);
				} else if (filteredNodes.length > 0) {
					scrollToNode(filteredNodes[0].node.node.id);
				}
				break;
			case 'Home':
				event.preventDefault();
				if (filteredNodes.length > 0) focusItem(0);
				break;
			case 'End':
				event.preventDefault();
				if (filteredNodes.length > 0) focusItem(filteredNodes.length - 1);
				break;
		}
	}

	function handleButtonKeydown(event: KeyboardEvent, index: number) {
		switch (event.key) {
			case 'ArrowDown':
				event.preventDefault();
				if (index < filteredNodes.length - 1) focusItem(index + 1);
				break;
			case 'ArrowUp':
				event.preventDefault();
				if (index > 0) {
					focusItem(index - 1);
				} else {
					focusedIndex = -1;
					searchInput?.focus();
				}
				break;
			case 'Home':
				event.preventDefault();
				focusItem(0);
				break;
			case 'End':
				event.preventDefault();
				focusItem(filteredNodes.length - 1);
				break;
			case 'Escape':
				event.preventDefault();
				collapsed = true;
				break;
			case 'Enter':
			case ' ':
				event.preventDefault();
				scrollToNode(filteredNodes[index].node.node.id);
				break;
		}
	}
</script>

<div
	class="flex-shrink-0 transition-all duration-200 {collapsed
		? 'w-10'
		: 'w-64'} sticky self-start overflow-y-auto border-r border-gray-200 bg-white"
	style="top: {topOffset}px; max-height: calc(100vh - {topOffset}px)"
>
	<!-- Header -->
	<div class="flex items-center justify-between p-2 border-b border-gray-100">
		{#if !collapsed}
			<span class="text-sm font-semibold text-gray-700">Table of Contents</span>
		{/if}
		<button
			class="btn btn-sm preset-tonal-surface"
			onclick={toggleCollapse}
			title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
		>
			<i class="fa-solid {collapsed ? 'fa-angles-right' : 'fa-angles-left'} text-xs"></i>
		</button>
	</div>

	{#if !collapsed}
		<!-- Search -->
		<div class="px-2 py-2 border-b border-gray-100">
			<div class="relative">
				<input
					bind:this={searchInput}
					bind:value={searchQuery}
					onkeydown={handleSearchKeydown}
					type="text"
					placeholder="Search nodes..."
					class="w-full px-3 py-1.5 pr-7 text-xs border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
				/>
				<div class="absolute inset-y-0 right-0 flex items-center pr-2">
					{#if searchQuery}
						<button
							onclick={clearSearch}
							class="text-gray-400 hover:text-gray-600 transition-colors"
							tabindex={-1}
						>
							<i class="fa-solid fa-times text-[10px]"></i>
						</button>
					{:else}
						<i class="fa-solid fa-search text-gray-300 text-[10px]"></i>
					{/if}
				</div>
			</div>
		</div>

		<!-- Bulk expand/collapse — only shown when there are collapsible branches -->
		{#if $rootNodesStore.some((n) => n.children.length > 0)}
			<div class="px-2 pb-1 flex items-center gap-1 border-b border-gray-100">
				<button
					type="button"
					class="flex-1 inline-flex items-center justify-center gap-1 px-2 py-1 text-[10px] text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
					onclick={() => tocCollapsed.collapseAll(collectAllParentIds($rootNodesStore))}
					title="Collapse all"
					aria-label="Collapse all"
				>
					<i class="fa-solid fa-angles-up text-[10px]"></i>
					<span>Collapse all</span>
				</button>
				<button
					type="button"
					class="flex-1 inline-flex items-center justify-center gap-1 px-2 py-1 text-[10px] text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
					onclick={() => tocCollapsed.expandAll()}
					title="Expand all"
					aria-label="Expand all"
				>
					<i class="fa-solid fa-angles-down text-[10px]"></i>
					<span>Expand all</span>
				</button>
			</div>
		{/if}

		<!-- Navigation -->
		<nav class="toc-nav p-2 space-y-0.5" role="navigation" aria-label="Table of Contents">
			<!-- Framework metadata entry (pinned, hidden during search) -->
			{#if !searchQuery}
				<button
					class="w-full text-left px-2 py-2 text-xs rounded-md transition-colors flex items-center gap-1.5
						{$activeSectionStore === FRAMEWORK_ID
						? 'bg-primary-100 text-primary-700 font-medium border-l-2 border-primary-500'
						: 'text-gray-600 hover:bg-gray-100'}"
					onclick={() => scrollToNode(FRAMEWORK_ID)}
					aria-current={$activeSectionStore === FRAMEWORK_ID ? 'location' : undefined}
				>
					<i class="fa-solid fa-file-lines text-gray-400 text-[10px]"></i>
					<span>Framework</span>
				</button>

				<hr class="my-1 border-gray-100" />
			{/if}

			<!-- Node entries -->
			{#each filteredNodes as entry, index (`toc-${index}-${entry.node.node.id}`)}
				{@const n = entry.node.node}
				{@const hasChildren = entry.node.children.length > 0}
				{@const isCollapsed = tocCollapsedSet.has(n.id)}
				{@const icon = n.display_mode === 'splash'
					? 'fa-display text-purple-400'
					: n.assessable && hasChildren
						? 'fa-square-check text-blue-400'
						: n.assessable
							? 'fa-square-check text-green-500'
							: hasChildren
								? 'fa-folder text-gray-400'
								: 'fa-circle-dot text-gray-300'}
				<div class="flex items-center" style="padding-left: {0.5 + entry.depth * 0.75}rem">
					{#if hasChildren}
						<button
							type="button"
							class="flex-shrink-0 w-4 h-4 flex items-center justify-center text-gray-400 hover:text-gray-600"
							onclick={(e) => {
								e.stopPropagation();
								tocCollapsed.toggle(n.id);
							}}
							title={isCollapsed ? 'Expand' : 'Collapse'}
							aria-label={isCollapsed ? 'Expand' : 'Collapse'}
						>
							<i class="fa-solid {isCollapsed ? 'fa-chevron-right' : 'fa-chevron-down'} text-[8px]"
							></i>
						</button>
					{:else}
						<span class="w-4 h-4 flex-shrink-0"></span>
					{/if}

					<button
						bind:this={navigationButtons[index]}
						class="flex-1 text-left py-1.5 text-xs rounded-md transition-colors flex items-center gap-1.5
							{$activeSectionStore === n.id
								? 'bg-primary-100 text-primary-700 font-medium border-l-2 border-primary-500'
								: 'text-gray-600 hover:bg-gray-100'}
							{focusedIndex === index ? 'ring-2 ring-primary-300' : ''}"
						onclick={() => {
							focusedIndex = index;
							scrollToNode(n.id);
						}}
						onkeydown={(e) => handleButtonKeydown(e, index)}
						onfocus={() => (focusedIndex = index)}
						aria-current={$activeSectionStore === n.id ? 'location' : undefined}
						aria-label="Jump to: {n.ref_id || n.name || 'Untitled'}"
						tabindex={focusedIndex === index ? 0 : -1}
					>
						<i class="fa-solid {icon} text-[10px] flex-shrink-0"></i>
						<span class="truncate flex-1">{n.ref_id || n.name || 'Untitled'}</span>
						{#if $activeLanguageStore && hasUntranslated([entry.node], $activeLanguageStore)}
							<span class="text-amber-500 text-[8px] flex-shrink-0" title="Has untranslated items"
								>&#9679;</span
							>
						{/if}
						{#if hasChildren}
							<span class="text-[10px] text-gray-400 ml-1 tabular-nums flex-shrink-0"
								>{countDescendants([entry.node])}</span
							>
						{/if}
					</button>
				</div>
			{/each}

			<!-- Empty state -->
			{#if $rootNodesStore.length === 0}
				<p class="text-xs text-gray-400 px-2 py-4">No nodes yet</p>
			{:else if searchQuery && filteredNodes.length === 0}
				<div class="text-center py-4">
					<p class="text-xs text-gray-400">No matching nodes</p>
					<button
						onclick={clearSearch}
						class="mt-1 text-xs text-primary-600 hover:text-primary-800 underline"
					>
						Clear search
					</button>
				</div>
			{/if}
		</nav>

		<!-- Footer: search result count -->
		{#if searchQuery && filteredNodes.length > 0}
			<div class="px-2 py-1.5 border-t border-gray-100 text-[10px] text-gray-400 text-center">
				{filteredNodes.length} of {allEntries.length} nodes
			</div>
		{/if}
	{/if}
</div>

<style>
	.toc-nav::-webkit-scrollbar {
		width: 4px;
	}
	.toc-nav::-webkit-scrollbar-track {
		background: #f1f5f9;
		border-radius: 2px;
	}
	.toc-nav::-webkit-scrollbar-thumb {
		background: #cbd5e1;
		border-radius: 2px;
	}
	.toc-nav::-webkit-scrollbar-thumb:hover {
		background: #94a3b8;
	}
</style>
