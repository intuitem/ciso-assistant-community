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

	function handleSelect(folder: Folder) {
		setFocusMode(folder.id, folder.str || folder.name);
		isOpen = false;
		// Invalidate all data to refetch with new focus scope
		invalidateAll();
	}

	function handleClear() {
		clearFocusMode();
		isOpen = false;
		// Invalidate all data to refetch without focus scope
		invalidateAll();
	}

	function toggleDropdown() {
		isOpen = !isOpen;
	}

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.focus-mode-selector')) {
			isOpen = false;
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
				: 'bg-surface-100-900 text-surface-600-400 hover:bg-surface-200-800 px-3 py-1.5'}"
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
			class="absolute right-0 top-full mt-1 w-64 max-h-80 overflow-y-auto bg-surface-50-950 rounded-lg shadow-lg border border-surface-200-800 z-50"
		>
			<div class="p-2 border-b border-surface-100-900">
				<span class="text-xs font-semibold text-surface-600-400 uppercase tracking-wide">
					{m.selectDomain?.() ?? 'Select domain'}
				</span>
			</div>
			<ul class="py-1">
				{#if $focusMode.id}
					<li>
						<button
							onclick={handleClear}
							class="w-full px-3 py-2 text-left text-sm hover:bg-surface-50-950 flex items-center gap-2 text-surface-600-400"
						>
							<i class="fa-solid fa-globe text-surface-400-600"></i>
							{m.allDomains?.() ?? 'All domains'}
						</button>
					</li>
					<li class="border-t border-surface-100-900"></li>
				{/if}
				{#each domainFolders as folder (folder.id)}
					<li>
						<button
							onclick={() => handleSelect(folder)}
							class="w-full px-3 py-2 text-left text-sm hover:bg-indigo-50 flex items-center gap-2
								{$focusMode.id === folder.id ? 'bg-indigo-100 text-indigo-700' : 'text-surface-700-300'}"
						>
							<i
								class="fa-solid fa-folder {$focusMode.id === folder.id
									? 'text-indigo-500'
									: 'text-surface-400-600'}"
							></i>
							<span class="truncate">{folder.str || folder.name}</span>
							{#if $focusMode.id === folder.id}
								<i class="fa-solid fa-check ml-auto text-indigo-500"></i>
							{/if}
						</button>
					</li>
				{/each}
			</ul>
		</div>
	{:else if isOpen && domainFolders.length === 0}
		<div
			class="absolute right-0 top-full mt-1 w-64 bg-surface-50-950 rounded-lg shadow-lg border border-surface-200-800 z-50 p-4"
		>
			<p class="text-sm text-surface-600-400 text-center">
				{m.noDomainsAvailable?.() ?? 'No domains available'}
			</p>
		</div>
	{/if}
</div>
