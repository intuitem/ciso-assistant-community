<script lang="ts">
	import { browser } from '$app/environment';
	import { Command } from 'cmdk-sv';
	import { goto } from '$app/navigation';
	import { onMount, onDestroy } from 'svelte';

	let open = false;

	// Custom case-insensitive filter
	function caseInsensitiveFilter(value: string, search: string) {
		// Normalize both value and search to lowercase for comparison
		return value.toLowerCase().includes(search.toLowerCase()) ? 1 : 0;
	}

	// Keyboard shortcut handler
	function handleKeydown(e: KeyboardEvent) {
		if (browser && (e.metaKey || e.ctrlKey) && e.key === 'k') {
			e.preventDefault();
			open = !open;
		}
	}

	// Navigation commands
	const navigationCommands = [
		{
			label: 'Home',
			value: '/',
			onSelect: () => goto('/')
		},
		{
			label: 'About',
			value: '/about',
			onSelect: () => goto('/about')
		},
		{
			label: 'Settings',
			value: '/settings',
			onSelect: () => goto('/settings')
		}
	];

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

<Command.Dialog bind:open label="Command Menu">
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
		@apply fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm;
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
