<script lang="ts">
	import { browser } from '$app/environment';
	import { safeTranslate } from '$lib/utils/i18n';
	import { navigationLinks } from './paletteData';
	import { goto } from '$lib/utils/breadcrumbs';

	let opened = $state(false);
	let searchInput: HTMLElement | null = $state(null);

	// Generate navigation commands with automatic close
	const navigationCommands = navigationLinks.map((link) => ({
		label: safeTranslate(link.label),
		value: link.href,
		onSelect: () => {
			opened = false;
			goto(link.href, { label: link.label, breadcrumbAction: 'replace' });
		}
	}));

	let selected = $state(0);
	let searchText = $state('');
	let filteredNavigationCommands = $derived(
		navigationCommands.filter(
			(link) => link.label.toLowerCase().indexOf(searchText.toLowerCase()) >= 0
		)
	);
	$effect(() => {
		if (selected >= filteredNavigationCommands.length) {
			selected = 0;
		}
	});
	$effect(() => {
		if (opened) {
			searchInput?.focus();
		}
	});

	function handleKeydown(e: KeyboardEvent) {
		if (!browser) return;
		if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
			e.preventDefault();
			searchText = '';
			selected = 0;
			opened = !opened;
		}
		if (!opened) return;

		if (e.key === 'Escape') {
			opened = false;
		} else if (e.key === 'ArrowDown') {
			if (selected === navigationLinks.length - 1) return;
			selected++;
			document
				.querySelector(`[data-cmdk-nav-btn]:nth-of-type(${selected + 1})`)
				?.scrollIntoView(false);
		} else if (e.key === 'ArrowUp') {
			if (selected === 0) return;
			selected--;
			document.querySelector(`[data-cmdk-nav-btn]:nth-of-type(${selected + 1})`)?.scrollIntoView();
		} else if (e.key === 'Enter') {
			const selectedLink = filteredNavigationCommands[selected];
			if (selectedLink) filteredNavigationCommands[selected].onSelect();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if opened}
	<div
		class="backdrop-blur-xs fixed inset-0 z-[9999] w-full h-full m-auto flex items-center justify-center bg-black/50"
	>
		<div class="h-auto overflow-hidden flex flex-col max-h-88 w-md rounded-lg">
			<input
				class="w-full bg-white px-4 py-3 border-b border-gray-200 outline-none focus:border-blue-800"
				type="text"
				bind:value={searchText}
				bind:this={searchInput}
				placeholder="Type a command..."
			/>
			{#if filteredNavigationCommands.length > 0}
				<span class="bg-white py-2 px-4 text-xs uppercase text-gray-500">Navigation</span>
			{:else}
				<span class="bg-white py-2 px-1 text-black">No results found.</span>
			{/if}
			<div class="overflow-auto flex flex-col">
				{#each filteredNavigationCommands as navigationCommand, index}
					{#if navigationCommand.label.toLowerCase().indexOf(searchText.toLowerCase()) >= 0}
						<button
							class="navigation-btn text-left py-2 px-4 text-black {selected === index
								? 'bg-gray-100'
								: 'bg-white'}"
							data-cmdk-nav-btn=""
							onmouseenter={() => {
								selected = index;
							}}
							onclick={navigationCommand.onSelect}>{navigationCommand.label}</button
						>
					{/if}
				{/each}
			</div>
		</div>
	</div>
{/if}
