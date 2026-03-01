<script lang="ts">
	import { focusMode, setFocusMode, clearFocusMode } from '$lib/utils/stores';
	import { invalidateAll } from '$app/navigation';
	import * as m from '$paraglide/messages';
	import FolderTreeNode, { type TreeNode } from './FolderTreeNode.svelte';

	interface Props {
		orgTree?: TreeNode;
	}

	let { orgTree }: Props = $props();

	// Top-level nodes from the org tree (direct children of Global)
	const topNodes = $derived(orgTree?.children ?? []);
	const hasNodes = $derived(topNodes.length > 0);

	let isOpen = $state(false);
	let searchQuery = $state('');
	let sortAsc = $state(true);

	// Debounced query: avoids cascading DOM updates on every keystroke
	let debouncedQuery = $state('');
	$effect(() => {
		const q = searchQuery;
		const t = setTimeout(() => {
			debouncedQuery = q;
		}, 150);
		return () => clearTimeout(t);
	});

	// O(N) DFS: collects all directly-matching nodes with their ancestor paths
	type SearchResult = { node: TreeNode; path: string[] };
	const searchData = $derived.by(() => {
		const q = debouncedQuery.trim().toLowerCase();
		if (!q) return null;
		const results: SearchResult[] = [];
		function visit(n: TreeNode, ancestors: string[]) {
			if (n.name.toLowerCase().includes(q) && n.uuid) {
				results.push({ node: n, path: ancestors });
			}
			(n.children ?? []).forEach((c) => visit(c, [...ancestors, n.name]));
		}
		topNodes.forEach((n) => visit(n, []));
		results.sort((a, b) => a.node.name.localeCompare(b.node.name));
		return results;
	});

	const hasAnyResult = $derived(!searchData || searchData.length > 0);

	const sortedTopNodes = $derived(
		sortAsc
			? [...topNodes].sort((a, b) => a.name.localeCompare(b.name))
			: [...topNodes].sort((a, b) => b.name.localeCompare(a.name))
	);

	function handleSelect(id: string, name: string) {
		setFocusMode(id, name);
		isOpen = false;
		searchQuery = '';
		invalidateAll();
	}

	function handleClear() {
		clearFocusMode();
		isOpen = false;
		searchQuery = '';
		invalidateAll();
	}

	function toggleDropdown() {
		if (isOpen) searchQuery = '';
		isOpen = !isOpen;
	}

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.focus-mode-selector')) {
			isOpen = false;
			searchQuery = '';
		}
	}

	$effect(() => {
		if (isOpen) {
			document.addEventListener('click', handleClickOutside);
			return () => document.removeEventListener('click', handleClickOutside);
		}
	});
</script>

<div class="focus-mode-selector relative">
	<div class="relative">
		<button
			onclick={toggleDropdown}
			class="flex items-center gap-2 rounded-lg text-sm font-medium transition-all duration-200
				{$focusMode.id
				? 'bg-indigo-100 text-indigo-700 ring-2 ring-indigo-300 hover:bg-indigo-200 pl-3 pr-8 py-1.5'
				: 'bg-slate-100 text-slate-600 hover:bg-slate-200 px-3 py-1.5'}"
			title={m.focusModeTooltip()}
		>
			<i class="fa-solid fa-crosshairs text-xs"></i>
			<span class="max-w-32 truncate">
				{$focusMode.name ?? m.allDomains()}
			</span>
			{#if !$focusMode.id}
				<i class="fa-solid fa-chevron-down text-xs"></i>
			{/if}
		</button>
		{#if $focusMode.id}
			<button
				onclick={(e) => {
					e.stopPropagation();
					handleClear();
				}}
				class="absolute right-1 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-indigo-300 transition-colors z-10"
				title={m.clearFocus()}
			>
				<i class="fa-solid fa-xmark text-xs"></i>
			</button>
		{/if}
	</div>

	{#if isOpen && hasNodes}
		<div
			class="absolute right-0 top-full mt-1 w-72 bg-white rounded-lg shadow-lg border border-slate-200 z-50 flex flex-col"
			style="max-height: 26rem"
		>
			<!-- Header: label + sort toggle -->
			<div class="p-2 border-b border-slate-100 space-y-2 flex-shrink-0">
				<div class="flex items-center justify-between">
					<span class="text-xs font-semibold text-slate-500 uppercase tracking-wide">
						{m.selectDomain()}
					</span>
					{#if !searchData}
						<button
							type="button"
							onclick={(e) => {
								e.stopPropagation();
								sortAsc = !sortAsc;
							}}
							class="flex items-center gap-1 text-xs text-slate-500 hover:text-indigo-600 transition-colors"
							title={sortAsc ? m.sortDescending() : m.sortAscending()}
						>
							<i class={sortAsc ? 'fa-solid fa-arrow-down-a-z' : 'fa-solid fa-arrow-down-z-a'}></i>
							<span>{sortAsc ? 'A→Z' : 'Z→A'}</span>
						</button>
					{/if}
				</div>
				<div class="relative">
					<i
						class="fa-solid fa-magnifying-glass absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 text-xs pointer-events-none"
					></i>
					<input
						type="search"
						class="w-full pl-6 pr-2 py-1 text-sm border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-indigo-300"
						placeholder={m.searchPlaceholder()}
						bind:value={searchQuery}
						onclick={(e) => e.stopPropagation()}
					/>
				</div>
			</div>
			{#if $focusMode.id}
				<div class="flex-shrink-0 border-b border-slate-100">
					<button
						onclick={handleClear}
						class="w-full px-3 py-2 text-left text-sm hover:bg-slate-50 flex items-center gap-2 text-slate-600"
					>
						<i class="fa-solid fa-globe text-slate-400"></i>
						{m.allDomains()}
					</button>
				</div>
			{/if}

			<ul class="list-none p-0 m-0 overflow-y-auto flex-1 py-1 px-1">
				{#if searchData}
					<!-- Flat results with breadcrumb path when search is active -->
					{#each searchData as result (result.node.uuid)}
						<li class="list-none">
							<button
								type="button"
								class="w-full px-2 py-1.5 text-left hover:bg-indigo-50 rounded transition-colors
									{$focusMode.id === String(result.node.uuid) ? 'bg-indigo-100' : ''}"
								onclick={(e) => {
									e.stopPropagation();
									handleSelect(String(result.node.uuid), result.node.name);
								}}
								title={[...result.path, result.node.name].join(' / ')}
							>
								{#if result.path.length > 0}
									<div class="text-[10px] text-slate-400 truncate leading-tight mb-0.5">
										{result.path.length > 2
											? '… / ' + result.path.slice(-2).join(' / ')
											: result.path.join(' / ')}
									</div>
								{/if}
								<div class="flex items-center gap-1.5">
									<i
										class="fa-solid fa-folder flex-shrink-0 text-xs {$focusMode.id ===
										String(result.node.uuid)
											? 'text-indigo-500'
											: 'text-slate-400'}"
									></i>
									<span class="truncate text-sm font-semibold text-indigo-700"
										>{result.node.name}</span
									>
									{#if $focusMode.id === String(result.node.uuid)}
										<i class="fa-solid fa-check ml-auto flex-shrink-0 text-indigo-500 text-xs"></i>
									{/if}
								</div>
							</button>
						</li>
					{/each}
					{#if searchData.length === 0}
						<li class="px-3 py-2 text-sm text-slate-400 text-center list-none">
							{m.noResultFound()}
						</li>
					{/if}
				{:else}
					<!-- Tree view when not searching -->
					{#each sortedTopNodes as node (node.uuid ?? node.name)}
						<FolderTreeNode
							{node}
							{sortAsc}
							focusId={$focusMode.id ?? null}
							onSelect={handleSelect}
							depth={0}
						/>
					{/each}
				{/if}
			</ul>
		</div>
	{:else if isOpen && !hasNodes}
		<div
			class="absolute right-0 top-full mt-1 w-72 bg-white rounded-lg shadow-lg border border-slate-200 z-50 p-4"
		>
			<p class="text-sm text-slate-500 text-center">
				{m.noDomainsAvailable()}
			</p>
		</div>
	{/if}
</div>
