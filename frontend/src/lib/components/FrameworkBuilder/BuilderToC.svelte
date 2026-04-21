<script lang="ts">
	import { onMount } from 'svelte';
	import { getBuilderContext } from './builder-state';

	import type { BuilderNode } from './builder-state';

	const builder = getBuilderContext();
	const {
		rootNodes: sectionsStore,
		activeSection: activeSectionStore,
		isScrolling: isScrollingStore,
		activeLanguage: activeLanguageStore
	} = builder;

	let collapsed = $state(false);
	let searchQuery = $state('');
	let focusedIndex = $state(-1);
	let searchInput = $state<HTMLInputElement>();
	let navigationButtons = $state<HTMLButtonElement[]>([]);
	let topOffset = $state(0);

	const FRAMEWORK_ID = '__framework__';

	let filteredSections = $derived(
		searchQuery
			? $sectionsStore.filter((s) => {
					const label = s.node.ref_id || s.node.name || '';
					return label.toLowerCase().includes(searchQuery.toLowerCase());
				})
			: $sectionsStore
	);

	$effect(() => {
		if (filteredSections.length > 0 && focusedIndex >= filteredSections.length) {
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

	/** Check if a section has any untranslated items for the active language */
	function hasUntranslated(reqs: BuilderNode[], lang: string): boolean {
		for (const r of reqs) {
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

	/** Count all requirements (including nested children) in a section */
	function countRequirements(reqs: { children: { children: unknown[] }[] }[]): number {
		let count = 0;
		for (const r of reqs) {
			count++;
			if (r.children?.length) {
				count += countRequirements(r.children as typeof reqs);
			}
		}
		return count;
	}

	function scrollToSection(sectionId: string) {
		isScrollingStore.set(true);
		activeSectionStore.set(sectionId);

		if (sectionId === FRAMEWORK_ID) {
			const container = document.querySelector('[data-framework-metadata]');
			if (container) {
				container.scrollIntoView({ behavior: 'smooth', block: 'start' });
			}
		} else {
			const el = document.querySelector(`[data-section-id="${sectionId}"]`);
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
		if (index >= 0 && index < filteredSections.length && navigationButtons[index]) {
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
				if (filteredSections.length > 0) {
					focusItem(focusedIndex < 0 ? 0 : Math.min(focusedIndex + 1, filteredSections.length - 1));
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
					scrollToSection(filteredSections[focusedIndex].node.id);
				} else if (filteredSections.length > 0) {
					scrollToSection(filteredSections[0].node.id);
				}
				break;
			case 'Home':
				event.preventDefault();
				if (filteredSections.length > 0) focusItem(0);
				break;
			case 'End':
				event.preventDefault();
				if (filteredSections.length > 0) focusItem(filteredSections.length - 1);
				break;
		}
	}

	function handleButtonKeydown(event: KeyboardEvent, index: number) {
		switch (event.key) {
			case 'ArrowDown':
				event.preventDefault();
				if (index < filteredSections.length - 1) focusItem(index + 1);
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
				focusItem(filteredSections.length - 1);
				break;
			case 'Escape':
				event.preventDefault();
				collapsed = true;
				break;
			case 'Enter':
			case ' ':
				event.preventDefault();
				scrollToSection(filteredSections[index].node.id);
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
					placeholder="Search sections..."
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

		<!-- Navigation -->
		<nav class="toc-nav p-2 space-y-0.5" role="navigation" aria-label="Table of Contents">
			<!-- Framework metadata entry (pinned, hidden during search) -->
			{#if !searchQuery}
				<button
					class="w-full text-left px-2 py-2 text-xs rounded-md transition-colors flex items-center gap-1.5
						{$activeSectionStore === FRAMEWORK_ID
						? 'bg-primary-100 text-primary-700 font-medium border-l-2 border-primary-500'
						: 'text-gray-600 hover:bg-gray-100'}"
					onclick={() => scrollToSection(FRAMEWORK_ID)}
					aria-current={$activeSectionStore === FRAMEWORK_ID ? 'location' : undefined}
				>
					<i class="fa-solid fa-file-lines text-gray-400 text-[10px]"></i>
					<span>Framework</span>
				</button>

				<hr class="my-1 border-gray-100" />
			{/if}

			<!-- Section entries -->
			{#each filteredSections as section, index (`toc-${index}-${section.node.id}`)}
				<button
					bind:this={navigationButtons[index]}
					class="w-full text-left px-2 py-2 text-xs rounded-md transition-colors flex items-center
						{$activeSectionStore === section.node.id
						? 'bg-primary-100 text-primary-700 font-medium border-l-2 border-primary-500'
						: 'text-gray-600 hover:bg-gray-100'}
						{focusedIndex === index ? 'ring-2 ring-primary-300' : ''}"
					onclick={() => {
						focusedIndex = index;
						scrollToSection(section.node.id);
					}}
					onkeydown={(e) => handleButtonKeydown(e, index)}
					onfocus={() => (focusedIndex = index)}
					aria-current={$activeSectionStore === section.node.id ? 'location' : undefined}
					aria-label="Jump to section: {section.node.ref_id || section.node.name || 'Untitled'}"
					tabindex={focusedIndex === index ? 0 : -1}
				>
					<span class="truncate flex-1"
						>{section.node.ref_id || section.node.name || 'Untitled'}</span
					>
					{#if $activeLanguageStore && hasUntranslated(section.children, $activeLanguageStore)}
						<span class="text-amber-500 text-[8px] flex-shrink-0" title="Has untranslated items"
							>&#9679;</span
						>
					{/if}
					<span class="text-[10px] text-gray-400 ml-1 tabular-nums flex-shrink-0"
						>{countRequirements(section.children)}</span
					>
				</button>
			{/each}

			<!-- Empty state -->
			{#if $sectionsStore.length === 0}
				<p class="text-xs text-gray-400 px-2 py-4">No sections yet</p>
			{:else if searchQuery && filteredSections.length === 0}
				<div class="text-center py-4">
					<p class="text-xs text-gray-400">No matching sections</p>
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
		{#if searchQuery && filteredSections.length > 0}
			<div class="px-2 py-1.5 border-t border-gray-100 text-[10px] text-gray-400 text-center">
				{filteredSections.length} of {$sectionsStore.length} sections
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
