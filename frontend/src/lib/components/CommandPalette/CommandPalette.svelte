<script lang="ts">
	import { run } from 'svelte/legacy';

	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import { Command } from 'cmdk-sv';
	import { onMount, onDestroy } from 'svelte';
	import { writable } from 'svelte/store';
	import { safeTranslate } from '$lib/utils/i18n';
	import { navigationLinks } from './paletteData.ts';
	import { goto } from '$lib/utils/breadcrumbs';

	// Create a store for command palette visibility
	export const commandPaletteOpen = writable(false);

	// Custom case-insensitive filter
	function caseInsensitiveFilter(value: string, search: string) {
		return value.toLowerCase().includes(search.toLowerCase()) ? 1 : 0;
	}

	// Keyboard shortcut handler
	function handleKeydown(e: KeyboardEvent) {
		if (browser && (e.metaKey || e.ctrlKey) && e.key === 'k') {
			e.preventDefault();
			commandPaletteOpen.update((current) => !current);
		}
	}

	// Generate navigation commands with automatic close
	const navigationCommands = navigationLinks.map((link) => ({
		label: safeTranslate(link.label),
		value: link.href,
		onSelect: () => {
			commandPaletteOpen.set(false);
			goto(link.href, { label: link.label, breadcrumbAction: 'replace' });
		}
	}));

	// Close command palette on route change
	run(() => {
		if ($page.url.pathname) {
			commandPaletteOpen.set(false);
		}
	});

	// Add global event listener
	onMount(() => {
		if (browser) {
			window.addEventListener('keydown', handleKeydown);
		}
	});

	onDestroy(() => {
		if (browser) {
			window.removeEventListener('keydown', handleKeydown);
		}
	});
</script>

<Command.Dialog bind:open={$commandPaletteOpen} label="Command Menu">
	<Command.Root filter={caseInsensitiveFilter}>
		<Command.Input placeholder="Type a command..." />
		<Command.List>
			<Command.Empty>No results found.</Command.Empty>
			<Command.Group heading="Navigation">
				{#each navigationCommands as command}
					<Command.Item value={command.label} onSelect={command.onSelect}>
						{command.label}
					</Command.Item>
				{/each}
			</Command.Group>
			<Command.Separator />
		</Command.List>
	</Command.Root>
</Command.Dialog>

<style lang="postcss">
	/* Global styles for the command palette */
	:global([data-cmdk-dialog]) {
		@apply fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-2;
	}

	:global([data-cmdk-root]) {
		@apply w-full max-w-md bg-white rounded-lg shadow-xl border border-gray-200 overflow-hidden;
	}

	:global([data-cmdk-input]) {
		@apply w-full px-4 py-3 border-b border-gray-200 outline-none;
	}

	:global([data-cmdk-list]) {
		@apply max-h-[300px] overflow-y-auto;
	}

	:global([data-cmdk-item]) {
		@apply px-4 py-2 cursor-pointer hover:bg-gray-100
               focus:bg-gray-100 focus:outline-none;
	}

	:global([data-cmdk-item][data-selected='true']) {
		@apply bg-gray-100;
	}

	:global([data-cmdk-group-heading]) {
		@apply px-4 py-2 text-xs text-gray-500 uppercase;
	}
</style>
