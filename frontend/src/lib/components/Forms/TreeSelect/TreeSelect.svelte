<script lang="ts">
	import { onMount } from 'svelte';
	import { formFieldProxy, type SuperForm } from 'sveltekit-superforms';
	import * as m from '$paraglide/messages';
	import type { CacheLock } from '$lib/utils/types';
	import TreeSelectNode, { type TreeSelectItem } from './TreeSelectNode.svelte';

	interface Props {
		form: SuperForm<any>;
		/** The form field path */
		field: string;
		/** Already-normalised tree. The caller owns fetching and labelling. */
		nodes: TreeSelectItem[];
		label?: string;
		placeholder?: string;
		helpText?: string;
		nullable?: boolean;
		disabled?: boolean;
		hidden?: boolean;
		isLoading?: boolean;
		/** FontAwesome classes for the per-node glyph */
		icon?: string;
		cacheLock?: CacheLock;
		cachedValue?: any;
		/** Called whenever the selected value changes */
		onChange?: (value: any) => void;
		/** Called on mount with the initial value */
		mount?: (value: any) => void;
		/** Prune this node and its subtree, e.g. to prevent a parent cycle. */
		excludeSubtreeOf?: string | null;
		/** Shown when the current value is absent from the tree. */
		fallbackLabel?: string | null;
	}

	let {
		form,
		field,
		nodes,
		label = undefined,
		placeholder = undefined,
		helpText = undefined,
		nullable = true,
		disabled = false,
		hidden = false,
		isLoading = false,
		icon = 'fa-solid fa-sitemap',
		cacheLock = {
			promise: new Promise((res) => res(null)),
			resolve: (x: any) => x
		},
		cachedValue = $bindable(),
		onChange = () => {},
		mount: mountCallback = () => null,
		excludeSubtreeOf = null,
		fallbackLabel = null
	}: Props = $props();

	const { value, errors, constraints } = formFieldProxy(form, field);

	let isOpen = $state(false);
	let searchQuery = $state('');
	let searchInputEl = $state<HTMLInputElement | null>(null);
	let sortAsc = $state(true);
	let selectedLabel = $state('');
	let selectedPath = $state<string[]>([]);

	let debouncedQuery = $state('');
	$effect(() => {
		const q = searchQuery;
		const t = setTimeout(() => {
			debouncedQuery = q;
		}, 150);
		return () => clearTimeout(t);
	});

	function pruneExcluded(items: TreeSelectItem[]): TreeSelectItem[] {
		if (!excludeSubtreeOf) return items;
		return items
			.filter((n) => String(n.id) !== String(excludeSubtreeOf))
			.map((n) => ({ ...n, children: pruneExcluded(n.children ?? []) }));
	}

	const visibleNodes = $derived(pruneExcluded(nodes ?? []));
	const hasNodes = $derived(visibleNodes.length > 0);

	const sortedTopNodes = $derived(
		sortAsc
			? [...visibleNodes].sort((a, b) => a.label.localeCompare(b.label))
			: [...visibleNodes].sort((a, b) => b.label.localeCompare(a.label))
	);

	type SearchResult = { node: TreeSelectItem; path: string[] };

	const searchData = $derived.by(() => {
		const q = debouncedQuery.trim().toLowerCase();
		if (!q) return null;
		const results: SearchResult[] = [];
		function visit(n: TreeSelectItem, ancestors: string[]) {
			if (n.selectable && n.label.toLowerCase().includes(q)) {
				results.push({ node: n, path: ancestors });
			}
			(n.children ?? []).forEach((c) => visit(c, [...ancestors, n.label]));
		}
		visibleNodes.forEach((n) => visit(n, []));
		results.sort((a, b) => a.node.label.localeCompare(b.node.label));
		return results;
	});

	$effect(() => {
		const v = $value;
		if (!v) {
			selectedLabel = '';
			selectedPath = [];
			return;
		}
		function find(items: TreeSelectItem[], anc: string[]): SearchResult | null {
			for (const n of items) {
				if (String(n.id) === String(v)) return { node: n, path: anc };
				const found = find(n.children ?? [], [...anc, n.label]);
				if (found) return found;
			}
			return null;
		}
		const result = find(nodes ?? [], []);
		selectedLabel = result ? result.node.label : (fallbackLabel ?? '');
		selectedPath = result ? result.path : [];
	});

	$effect(() => {
		cachedValue = $value;
	});

	const selectorClass = `tree-select-${field.replace(/_/g, '-')}`;

	function handleSelect(id: string, itemLabel: string, path: string[] = []) {
		$value = id;
		selectedLabel = itemLabel;
		selectedPath = path;
		isOpen = false;
		searchQuery = '';
		onChange($value);
	}

	function handleClear(e: MouseEvent) {
		e.stopPropagation();
		$value = null;
		selectedLabel = '';
		selectedPath = [];
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
			queueMicrotask(() => searchInputEl?.focus());
			return () => document.removeEventListener('click', handleClickOutside);
		}
	});

	onMount(() => {
		if (hidden) return;
		// May never resolve in edit mode, so nothing else may depend on it.
		cacheLock.promise.then((cacheResult) => {
			if (cacheResult !== null && cacheResult !== undefined) {
				$value = cacheResult;
			}
			if ($value) mountCallback($value);
		});
	});
</script>

{#if hidden}
	<input type="hidden" name={field} value={$value ?? ''} />
{:else}
	<div data-testid="form-input-{field.replace(/_/g, '-')}" class="{selectorClass} relative">
		<!-- Needed for multipart/form-data forms (e.g. with file attachments) -->
		<input type="hidden" name={field} value={$value ?? ''} />
		{#if label !== undefined}
			<label class="block text-sm font-semibold mb-1" for="tree-select-btn-{field}">
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

		<div class="relative">
			<button
				id="tree-select-btn-{field}"
				type="button"
				onclick={toggleDropdown}
				{disabled}
				class="input bg-surface-100-900 flex items-center gap-2 w-full text-left px-3 py-2 text-sm
					{disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
					{$errors && $errors.length > 0 ? 'border-red-400' : ''}"
			>
				<i class="{icon} text-surface-500 flex-shrink-0 text-xs"></i>
				<span class="flex-1 min-w-0 truncate">
					{#if selectedLabel}
						{#if selectedPath.length > 0}
							<span class="text-surface-400-600 text-xs">{selectedPath.join(' / ')} / </span>
						{/if}
						<span class="text-surface-900-300">{selectedLabel}</span>
					{:else}
						<span class="text-surface-500">{placeholder ?? m.selectAnOption()}</span>
					{/if}
				</span>
				{#if isLoading}
					<i class="fa-solid fa-spinner animate-spin text-surface-500 text-xs flex-shrink-0"></i>
				{:else if !(selectedLabel && nullable)}
					<i
						class="fa-solid fa-chevron-down text-surface-500 text-xs flex-shrink-0 transition-transform {isOpen
							? 'rotate-180'
							: ''}"
					></i>
				{/if}
			</button>

			{#if selectedLabel && nullable && !disabled}
				<button
					type="button"
					onclick={handleClear}
					class="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-surface-200-800 transition-colors z-10 text-surface-500 hover:text-surface-600-400"
					title={m.clearSelection()}
				>
					<i class="fa-solid fa-xmark text-xs"></i>
				</button>
			{/if}
		</div>

		{#if helpText}
			<p class="text-xs text-surface-500 mt-0.5">{helpText}</p>
		{/if}

		{#if isOpen}
			<div
				class="absolute left-0 top-full mt-1 w-full min-w-64 bg-surface-50-950 rounded-lg shadow-lg border border-surface-200-800 z-50 flex flex-col"
				style="max-height: 22rem"
			>
				<div class="p-2 border-b border-surface-100-900 space-y-2 flex-shrink-0">
					<div class="flex items-center justify-between gap-1">
						<div class="relative w-full">
							<i
								class="fa-solid fa-magnifying-glass absolute left-2 top-1/2 -translate-y-1/2 text-surface-500 text-xs pointer-events-none"
							></i>
							<input
								type="text"
								class="input w-full pl-6 pr-2 py-1 text-sm border border-surface-200-800 rounded focus:outline-hidden focus:ring-1 focus:ring-indigo-300"
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
								class="flex items-center gap-1 text-xs text-surface-600-400 hover:text-indigo-600 transition-colors"
								title={sortAsc ? m.sortDescending() : m.sortAscending()}
							>
								<i class={sortAsc ? 'fa-solid fa-arrow-down-a-z' : 'fa-solid fa-arrow-down-z-a'}
								></i>
								<span>{sortAsc ? 'A→Z' : 'Z→A'}</span>
							</button>
						{/if}
					</div>
				</div>

				<ul class="list-none p-0 m-0 overflow-y-auto flex-1 py-1 px-1">
					{#if !hasNodes && !isLoading}
						<li class="px-3 py-2 text-sm text-surface-500 text-center list-none">
							{m.noResultFound()}
						</li>
					{:else if searchData}
						{#each searchData as result (result.node.id)}
							<li class="list-none">
								<button
									type="button"
									role="option"
									aria-selected={$value === String(result.node.id)}
									class="w-full px-2 py-1.5 text-left hover:bg-indigo-50 dark:hover:bg-indigo-950 rounded transition-colors
										{$value === String(result.node.id) ? 'bg-indigo-100 dark:bg-indigo-900' : ''}"
									onclick={(e) => {
										e.stopPropagation();
										handleSelect(String(result.node.id), result.node.label, result.path);
									}}
									title={[...result.path, result.node.label].join(' / ')}
								>
									{#if result.path.length > 0}
										<div class="text-[10px] text-surface-500 truncate leading-tight mb-0.5">
											{result.path.length > 2
												? '… / ' + result.path.slice(-2).join(' / ')
												: result.path.join(' / ')}
										</div>
									{/if}
									<div class="flex items-center gap-1.5">
										<i
											class="{icon} flex-shrink-0 text-xs {$value === String(result.node.id)
												? 'text-indigo-500'
												: 'text-surface-500'}"
										></i>
										<span
											class="truncate text-sm font-semibold text-indigo-700 dark:text-indigo-300"
										>
											{result.node.label}
										</span>
										{#if $value === String(result.node.id)}
											<i class="fa-solid fa-check ml-auto flex-shrink-0 text-indigo-500 text-xs"
											></i>
										{/if}
									</div>
								</button>
							</li>
						{/each}
						{#if searchData.length === 0}
							<li class="px-3 py-2 text-sm text-surface-500 text-center list-none">
								{m.noResultFound()}
							</li>
						{/if}
					{:else}
						{#each sortedTopNodes as node (node.id)}
							<TreeSelectNode
								{node}
								{sortAsc}
								{icon}
								selectedId={$value ? String($value) : null}
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
