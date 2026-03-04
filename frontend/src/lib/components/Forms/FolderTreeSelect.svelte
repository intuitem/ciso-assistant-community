<script lang="ts">
	import { onMount } from 'svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import * as m from '$paraglide/messages';
	import type { CacheLock } from '$lib/utils/types';
	import FolderTreeNode, { type TreeNode } from '../FocusMode/FolderTreeNode.svelte';

	interface Props {
		form: SuperForm<any>;
		// The form field path
		field: string;
		label?: string;
		helpText?: string;
		nullable?: boolean;
		disabled?: boolean;
		hidden?: boolean;
		cacheLock?: CacheLock;
		cachedValue?: any;
		// Called whenever the selected value changes
		onChange?: (value: any) => void;
		// Called on mount with the initial value
		mount?: (value: any) => void;
		/**
		 * Exclude a specific node from the tree (used for parent_folder to avoid
		 * selecting the folder itself as its own parent).
		 * Accepts the object itself or a plain UUID string.
		 */
		optionsSelf?: any;
		/**
		 * Defaults to ['DO', 'GL']
		 * previous optionsEndpoint="folders?content_type=DO&content_type=GL".
		 */
		contentTypes?: string[];
	}

	let {
		form,
		field,
		label = undefined,
		helpText = undefined,
		nullable = false,
		disabled = false,
		hidden = false,
		cacheLock = {
			promise: new Promise((res) => res(null)),
			resolve: (x: any) => x
		},
		cachedValue = $bindable(),
		onChange = () => {},
		mount: mountCallback = () => null,
		optionsSelf = null,
		contentTypes = ['DO', 'GL']
	}: Props = $props();

	const { value, errors, constraints } = formFieldProxy(form, field);

	let orgTree = $state<TreeNode | undefined>(undefined);
	let isOpen = $state(false);
	let searchQuery = $state('');
	let searchInputEl = $state<HTMLInputElement | null>(null);
	let sortAsc = $state(true);
	let selectedName = $state('');
	let isLoading = $state(false);

	let debouncedQuery = $state('');
	$effect(() => {
		const q = searchQuery;
		const t = setTimeout(() => {
			debouncedQuery = q;
		}, 150);
		return () => clearTimeout(t);
	});

	// Include the GL root as a flat first entry
	const topNodes = $derived(
		orgTree ? [{ ...orgTree, children: undefined }, ...(orgTree.children ?? [])] : []
	);
	const hasNodes = $derived(topNodes.length > 0);

	//  optionsSelf exclusion
	const excludedId = $derived(
		optionsSelf
			? String(
					typeof optionsSelf === 'object' ? (optionsSelf?.id ?? optionsSelf?.uuid) : optionsSelf
				)
			: null
	);

	/** Recursively prune the excluded node (and its subtree) from a node list. */
	function pruneExcluded(nodes: TreeNode[]): TreeNode[] {
		const eid = excludedId;
		if (!eid) return nodes;
		return nodes
			.filter((n) => n.uuid !== eid)
			.map((n) => ({
				...n,
				children: n.children ? pruneExcluded(n.children) : undefined
			}));
	}

	const sortedTopNodes = $derived.by(() => {
		const sorted = sortAsc
			? [...topNodes].sort((a, b) => a.name.localeCompare(b.name))
			: [...topNodes].sort((a, b) => b.name.localeCompare(a.name));
		return pruneExcluded(sorted);
	});

	//  Flat search results (DFS)
	type SearchResult = { node: TreeNode; path: string[] };

	const searchData = $derived.by(() => {
		const q = debouncedQuery.trim().toLowerCase();
		if (!q) return null;
		const results: SearchResult[] = [];
		function visit(n: TreeNode, ancestors: string[]) {
			const selectable = !n.content_type || contentTypes.includes(n.content_type);
			if (selectable && n.uuid !== excludedId && n.uuid && n.name.toLowerCase().includes(q)) {
				results.push({ node: n, path: ancestors });
			}
			(n.children ?? []).forEach((c) => visit(c, [...ancestors, n.name]));
		}
		topNodes.forEach((n) => visit(n, []));
		results.sort((a, b) => a.node.name.localeCompare(b.node.name));
		return results;
	});

	$effect(() => {
		const v = $value;
		if (v && orgTree) {
			function findName(n: TreeNode): string | null {
				if (n.uuid === String(v)) return n.name;
				for (const c of n.children ?? []) {
					const found = findName(c);
					if (found) return found;
				}
				return null;
			}
			const found = findName(orgTree);
			if (found) selectedName = found;
		} else if (!v) {
			selectedName = '';
		}
	});

	$effect(() => {
		cachedValue = $value;
	});

	//  Unique CSS class for click-outside detection
	const selectorClass = `folder-tree-select-${field.replace(/_/g, '-')}`;

	function handleSelect(id: string, name: string) {
		$value = id;
		selectedName = name;
		isOpen = false;
		searchQuery = '';
		onChange($value);
	}

	function handleClear(e: MouseEvent) {
		e.stopPropagation();
		$value = null;
		selectedName = '';
		isOpen = false;
		onChange(null);
	}

	function toggleDropdown() {
		if (disabled) return;
		if (isOpen) searchQuery = '';
		isOpen = !isOpen;
	}

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.' + selectorClass)) {
			isOpen = false;
			searchQuery = '';
		}
	}

	$effect(() => {
		if (isOpen) {
			document.addEventListener('click', handleClickOutside);
			// Focus search input on next tick so the element is in the DOM
			queueMicrotask(() => searchInputEl?.focus());
			return () => document.removeEventListener('click', handleClickOutside);
		}
	});

	//  Mount: fetch org_tree immediately; also handle cache lock independently
	onMount(() => {
		if (hidden) return;

		// Fetch org_tree right away

		isLoading = true;
		fetch('/folders/org_tree/?include_perimeters=false')
			.then((res) => {
				if (res.ok) return res.json();
			})
			.then((data) => {
				if (data) orgTree = data;
			})
			.catch((e) => console.error('FolderTreeSelect: failed to fetch org_tree', e))
			.finally(() => (isLoading = false));

		// Cache lock resolves when a cached value is available (create + caching=true).
		// In edit mode this promise may never resolve, so keep it independent.
		cacheLock.promise.then((cacheResult) => {
			if (cacheResult !== null && cacheResult !== undefined) {
				$value = cacheResult;
			}
			// Fire mount callback once we know the initial value
			if ($value) mountCallback($value);
		});
	});
</script>

<!-- Hidden input — renders only the hidden field, skipping all UI -->
{#if hidden}
	<input type="hidden" name={field} value={$value ?? ''} />
{:else}
	<div data-testid="form-input-{field.replace(/_/g, '-')}" class="{selectorClass} relative">
		<!-- Needed for multipart/form-data forms (e.g. with file attachments) -->
		<input type="hidden" name={field} value={$value ?? ''} />
		{#if label !== undefined}
			<label class="block text-sm font-semibold mb-1" for="folder-tree-select-btn-{field}">
				{label}
				{#if $constraints?.required}
					<span class="text-red-500">*</span>
				{/if}
			</label>
		{/if}

		{#if $errors && $errors.length > 0}
			<div class="mb-1">
				{#each $errors as error}
					<p class="text-error-500 text-xs font-medium">{error}</p>
				{/each}
			</div>
		{/if}

		<!-- Trigger button -->
		<div class="relative">
			<button
				id="folder-tree-select-btn-{field}"
				type="button"
				onclick={toggleDropdown}
				{disabled}
				class="input bg-surface-100 flex items-center gap-2 w-full text-left px-3 py-2 text-sm
					{disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
					{$errors && $errors.length > 0 ? 'border-red-400' : ''}"
			>
				<i class="fa-solid fa-folder text-slate-400 flex-shrink-0 text-xs"></i>
				<span class="flex-1 truncate {selectedName ? 'text-surface-900' : 'text-surface-500'}">
					{selectedName || m.selectDomain()}
				</span>
				{#if isLoading}
					<i class="fa-solid fa-spinner animate-spin text-slate-400 text-xs flex-shrink-0"></i>
				{:else if selectedName && nullable}
					<!-- clear button rendered separately below -->
				{:else}
					<i
						class="fa-solid fa-chevron-down text-slate-400 text-xs flex-shrink-0 transition-transform {isOpen
							? 'rotate-180'
							: ''}"
					></i>
				{/if}
			</button>

			<!-- Clear button -->
			{#if selectedName && nullable && !disabled}
				<button
					type="button"
					onclick={handleClear}
					class="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-slate-200 transition-colors z-10 text-slate-400 hover:text-slate-600"
					title={m.clearSelection()}
				>
					<i class="fa-solid fa-xmark text-xs"></i>
				</button>
			{/if}
		</div>

		{#if helpText}
			<p class="text-xs text-surface-500 mt-0.5">{helpText}</p>
		{/if}

		<!-- Dropdown -->
		{#if isOpen}
			<div
				class="absolute left-0 top-full mt-1 w-full min-w-64 bg-white rounded-lg shadow-lg border border-slate-200 z-50 flex flex-col"
				style="max-height: 22rem"
			>
				<!-- Header: sort toggle + search input -->
				<div class="p-2 border-b border-slate-100 space-y-2 flex-shrink-0">
					<div class="flex items-center justify-between gap-1">
						<div class="relative w-full">
							<i
								class="fa-solid fa-magnifying-glass absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 text-xs pointer-events-none"
							></i>
							<input
								type="text"
								class="w-full pl-6 pr-2 py-1 text-sm border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-indigo-300"
								placeholder={m.searchPlaceholder()}
								bind:value={searchQuery}
								bind:this={searchInputEl}
								onclick={(e) => e.stopPropagation()}
							/>
						</div>
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
								<i class={sortAsc ? 'fa-solid fa-arrow-down-a-z' : 'fa-solid fa-arrow-down-z-a'}
								></i>
								<span>{sortAsc ? 'A→Z' : 'Z→A'}</span>
							</button>
						{/if}
					</div>
				</div>

				<!-- List -->
				<ul class="list-none p-0 m-0 overflow-y-auto flex-1 py-1 px-1">
					{#if !hasNodes && !isLoading}
						<li class="px-3 py-2 text-sm text-slate-400 text-center list-none">
							{m.noDomainsAvailable()}
						</li>
					{:else if searchData}
						<!-- Flat results with breadcrumb -->
						{#each searchData as result (result.node.uuid)}
							<li class="list-none">
								<button
									type="button"
									role="option"
									aria-selected={$value === String(result.node.uuid)}
									class="w-full px-2 py-1.5 text-left hover:bg-indigo-50 rounded transition-colors
										{$value === String(result.node.uuid) ? 'bg-indigo-100' : ''}"
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
											class="fa-solid fa-folder flex-shrink-0 text-xs {$value ===
											String(result.node.uuid)
												? 'text-indigo-500'
												: 'text-slate-400'}"
										></i>
										<span class="truncate text-sm font-semibold text-indigo-700">
											{result.node.name}
										</span>
										{#if $value === String(result.node.uuid)}
											<i class="fa-solid fa-check ml-auto flex-shrink-0 text-indigo-500 text-xs"
											></i>
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
						{#each sortedTopNodes as node (node.uuid ?? node.name)}
							<FolderTreeNode
								{node}
								{sortAsc}
								{contentTypes}
								focusId={$value ? String($value) : null}
								onSelect={handleSelect}
								depth={0}
							/>
						{/each}
					{/if}
				</ul>
			</div>
		{/if}
	</div>
{/if}
