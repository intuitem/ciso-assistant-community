<script lang="ts">
	import { focusMode, setFocusMode, clearFocusMode } from '$lib/utils/stores';
	import { invalidateAll } from '$app/navigation';
	import * as m from '$paraglide/messages';

	interface Folder {
		id: string;
		str: string;
		name: string;
		content_type: string;
	}

	interface Props {
		folders?: Folder[];
	}

	let { folders = [] }: Props = $props();

	// Filter to only show Domain folders
	const domainFolders = $derived(folders.filter((f) => f.content_type === 'DOMAIN'));

	let isOpen = $state(false);
	let searchQuery = $state('');
	let sortAsc = $state(true);

	const filteredDomainFolders = $derived.by(() => {
		const filtered = domainFolders.filter((f) => {
			if (!searchQuery.trim()) return true;
			return (f.str || f.name).toLowerCase().includes(searchQuery.trim().toLowerCase());
		});
		return sortAsc ? filtered : [...filtered].reverse();
	});

	function handleSelect(folder: Folder) {
		setFocusMode(folder.id, folder.str || folder.name);
		isOpen = false;
		searchQuery = '';
		// Invalidate all data to refetch with new focus scope
		invalidateAll();
	}

	function handleClear() {
		clearFocusMode();
		isOpen = false;
		searchQuery = '';
		// Invalidate all data to refetch without focus scope
		invalidateAll();
	}

	function toggleDropdown() {
		if (isOpen) {
			searchQuery = '';
		}
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
			title={m.focusModeTooltip?.() ?? 'Focus on a specific domain'}
		>
			<i class="fa-solid fa-crosshairs text-xs"></i>
			<span class="max-w-32 truncate">
				{$focusMode.name ?? m.allDomains?.() ?? 'All domains'}
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
				title={m.clearFocus?.() ?? 'Clear focus'}
			>
				<i class="fa-solid fa-xmark text-xs"></i>
			</button>
		{/if}
	</div>

	{#if isOpen && domainFolders.length > 0}
		<div
			class="absolute right-0 top-full mt-1 w-64 max-h-80 overflow-y-auto bg-white rounded-lg shadow-lg border border-slate-200 z-50"
		>
			<div class="p-2 border-b border-slate-100 space-y-2">
				<div class="flex items-center justify-between">
					<span class="text-xs font-semibold text-slate-500 uppercase tracking-wide">
						{m.selectDomain?.() ?? 'Select domain'}
					</span>
					<button
						type="button"
						onclick={(e) => {
							e.stopPropagation();
							sortAsc = !sortAsc;
						}}
						class="flex items-center gap-1 text-xs text-slate-500 hover:text-indigo-600 transition-colors"
						title={sortAsc ? 'Sort Z → A' : 'Sort A → Z'}
					>
						<i class={sortAsc ? 'fa-solid fa-arrow-down-a-z' : 'fa-solid fa-arrow-down-z-a'}></i>
						<span>{sortAsc ? 'A→Z' : 'Z→A'}</span>
					</button>
				</div>
				<div class="relative">
					<i
						class="fa-solid fa-magnifying-glass absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 text-xs pointer-events-none"
					></i>
					<input
						type="search"
						class="w-full pl-6 pr-2 py-1 text-sm border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-indigo-300"
						placeholder={m.searchPlaceholder?.() ?? 'Search...'}
						bind:value={searchQuery}
						onclick={(e) => e.stopPropagation()}
					/>
				</div>
			</div>
			<ul class="py-1">
				{#if $focusMode.id}
					<li>
						<button
							onclick={handleClear}
							class="w-full px-3 py-2 text-left text-sm hover:bg-slate-50 flex items-center gap-2 text-slate-600"
						>
							<i class="fa-solid fa-globe text-slate-400"></i>
							{m.allDomains?.() ?? 'All domains'}
						</button>
					</li>
					<li class="border-t border-slate-100"></li>
				{/if}
				{#each filteredDomainFolders as folder (folder.id)}
					<li>
						<button
							onclick={() => handleSelect(folder)}
							class="w-full px-3 py-2 text-left text-sm hover:bg-indigo-50 flex items-center gap-2
								{$focusMode.id === folder.id ? 'bg-indigo-100 text-indigo-700' : 'text-slate-700'}"
						>
							<i
								class="fa-solid fa-folder {$focusMode.id === folder.id
									? 'text-indigo-500'
									: 'text-slate-400'}"
							></i>
							<span class="truncate">{folder.str || folder.name}</span>
							{#if $focusMode.id === folder.id}
								<i class="fa-solid fa-check ml-auto text-indigo-500"></i>
							{/if}
						</button>
					</li>
				{/each}
				{#if filteredDomainFolders.length === 0}
					<li class="px-3 py-2 text-sm text-slate-400 text-center">
						{m.noResults?.() ?? 'No results'}
					</li>
				{/if}
			</ul>
		</div>
	{:else if isOpen && domainFolders.length === 0}
		<div
			class="absolute right-0 top-full mt-1 w-64 bg-white rounded-lg shadow-lg border border-slate-200 z-50 p-4"
		>
			<p class="text-sm text-slate-500 text-center">
				{m.noDomainsAvailable?.() ?? 'No domains available'}
			</p>
		</div>
	{/if}
</div>
