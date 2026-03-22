<script lang="ts">
	import { browser } from '$app/environment';
	import { safeTranslate } from '$lib/utils/i18n';
	import { navigationLinks } from './paletteData';
	import { goto } from '$lib/utils/breadcrumbs';
	import { page } from '$app/state';
	import { navData } from '../SideBar/navData';
	import { getSidebarVisibleItems } from '$lib/utils/sidebar-config';
	import { expandChat } from '../ChatWidget/chatStore.svelte';
	import { m } from '$paraglide/messages';

	let opened = $state(false);
	let searchInput: HTMLElement | null = $state(null);

	const isMac = browser && navigator.platform.toUpperCase().indexOf('MAC') >= 0;
	const modifierKey = isMac ? '⌘' : 'Ctrl';

	// Generate navigation commands with automatic close
	const navigationCommands = navigationLinks.map((link) => ({
		label: safeTranslate(link.label),
		value: link.href,
		icon: link.icon,
		onSelect: () => {
			opened = false;
			goto(link.href, { label: link.label, breadcrumbAction: 'replace' });
		}
	}));

	// Action commands (non-navigation)
	const actionCommands = [
		{
			label: safeTranslate('openAssistant'),
			icon: 'fa-solid fa-robot',
			onSelect: () => {
				opened = false;
				expandChat();
			}
		}
	];

	const featureFlags = $derived(page.data?.featureflags ?? {});
	const sideBarVisibleItems = $derived(getSidebarVisibleItems(featureFlags));

	const visibilityKeyByHref = Object.fromEntries(
		(navData.items ?? [])
			.flatMap((section) => section.items ?? [])
			.filter((item) => item?.href && item?.name)
			.map((item) => [item.href, item.name])
	);

	// Strip accents/diacritics for accent-insensitive matching
	function normalize(str: string): string {
		return str
			.normalize('NFD')
			.replace(/[\u0300-\u036f]/g, '')
			.toLowerCase();
	}

	let selected = $state(0);
	let searchText = $state('');
	let filteredNavigationCommands = $derived(
		navigationCommands
			.filter((link) => normalize(link.label).includes(normalize(searchText)))
			.filter((link) => {
				const visibilityKey = visibilityKeyByHref[link.value];
				if (!visibilityKey) return true;
				return sideBarVisibleItems[visibilityKey] !== false;
			})
	);
	let filteredActionCommands = $derived(
		actionCommands.filter((cmd) => normalize(cmd.label).includes(normalize(searchText)))
	);

	$effect(() => {
		if (selected >= filteredNavigationCommands.length + filteredActionCommands.length) {
			selected = 0;
		}
	});
	$effect(() => {
		if (opened) {
			searchInput?.focus();
		}
	});

	export function toggle() {
		searchText = '';
		selected = 0;
		opened = !opened;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (!browser) return;
		if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
			e.preventDefault();
			toggle();
		}
		if (!opened) return;

		if (e.key === 'Escape') {
			opened = false;
		} else if (e.key === 'ArrowDown') {
			e.preventDefault();
			const total = filteredNavigationCommands.length + filteredActionCommands.length;
			if (selected < total - 1) {
				selected++;
			}
			document
				.querySelector(`[data-cmdk-nav-btn]:nth-of-type(${selected + 1})`)
				?.scrollIntoView({ block: 'nearest' });
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			if (selected > 0) {
				selected--;
			}
			document
				.querySelector(`[data-cmdk-nav-btn]:nth-of-type(${selected + 1})`)
				?.scrollIntoView({ block: 'nearest' });
		} else if (e.key === 'Enter') {
			const total = filteredNavigationCommands.length + filteredActionCommands.length;
			if (selected < filteredNavigationCommands.length) {
				filteredNavigationCommands[selected].onSelect();
			} else if (selected < total) {
				filteredActionCommands[selected - filteredNavigationCommands.length].onSelect();
			} else if (searchText.trim()) {
				// No match — launch universal search
				opened = false;
				goto(`/search?q=${encodeURIComponent(searchText.trim())}`, {
					label: 'search',
					breadcrumbAction: 'replace'
				});
			}
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if opened}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-[9999] flex items-start justify-center pt-[15vh] bg-black/50 backdrop-blur-sm"
		role="presentation"
		onclick={(e) => {
			if (e.target === e.currentTarget) opened = false;
		}}
		onkeydown={() => {}}
	>
		<!-- Palette container -->
		<div
			class="w-full max-w-lg mx-4 overflow-hidden rounded-xl bg-white shadow-2xl ring-1 ring-black/10 animate-in"
		>
			<!-- Search input -->
			<div class="flex items-center gap-3 px-4 border-b border-gray-200">
				<i class="fa-solid fa-magnifying-glass text-gray-400 text-sm"></i>
				<input
					class="w-full bg-transparent py-3.5 text-sm text-gray-900 placeholder-gray-400 outline-none border-none ring-0 focus:outline-none focus:border-none focus:ring-0 shadow-none"
					type="text"
					bind:value={searchText}
					bind:this={searchInput}
					placeholder={m.searchPagesAndObjects()}
				/>
				<button
					onclick={() => (opened = false)}
					class="shrink-0 rounded-md border border-gray-200 bg-gray-50 px-1.5 py-0.5 text-[10px] font-medium text-gray-500 hover:bg-gray-100 cursor-pointer"
				>
					ESC
				</button>
			</div>

			<!-- Results -->
			<div class="max-h-72 overflow-y-auto overscroll-contain">
				{#if filteredNavigationCommands.length > 0 || filteredActionCommands.length > 0}
					{#if filteredNavigationCommands.length > 0}
						<div class="px-3 py-2">
							<span class="text-[11px] font-semibold uppercase tracking-wider text-gray-400 px-1"
								>{m.commandPaletteNavigation()}</span
							>
						</div>
						<div class="px-2 pb-2">
							{#each filteredNavigationCommands as navigationCommand, index}
								<button
									class="w-full flex items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors cursor-pointer
										{selected === index ? 'bg-violet-50 text-violet-900' : 'text-gray-700 hover:bg-gray-50'}"
									data-cmdk-nav-btn=""
									onmouseenter={() => {
										selected = index;
									}}
									onclick={navigationCommand.onSelect}
								>
									{#if navigationCommand.icon}
										<i
											class="{navigationCommand.icon} w-4 text-center text-xs {selected === index
												? 'text-violet-500'
												: 'text-gray-400'}"
										></i>
									{/if}
									<span class="flex-1 truncate">{navigationCommand.label}</span>
									{#if selected === index}
										<span class="text-[10px] text-violet-400">↵</span>
									{/if}
								</button>
							{/each}
						</div>
					{/if}
					{#if filteredActionCommands.length > 0}
						<div class="px-3 py-2">
							<span class="text-[11px] font-semibold uppercase tracking-wider text-gray-400 px-1"
								>{m.commandPaletteActions()}</span
							>
						</div>
						<div class="px-2 pb-2">
							{#each filteredActionCommands as actionCommand, index}
								{@const globalIndex = filteredNavigationCommands.length + index}
								<button
									class="w-full flex items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors cursor-pointer
										{selected === globalIndex ? 'bg-violet-50 text-violet-900' : 'text-gray-700 hover:bg-gray-50'}"
									data-cmdk-nav-btn=""
									onmouseenter={() => {
										selected = globalIndex;
									}}
									onclick={actionCommand.onSelect}
								>
									{#if actionCommand.icon}
										<i
											class="{actionCommand.icon} w-4 text-center text-xs {selected === globalIndex
												? 'text-violet-500'
												: 'text-gray-400'}"
										></i>
									{/if}
									<span class="flex-1 truncate">{actionCommand.label}</span>
									{#if selected === globalIndex}
										<span class="text-[10px] text-violet-400">↵</span>
									{/if}
								</button>
							{/each}
						</div>
					{/if}
				{:else}
					<div class="flex flex-col items-center justify-center py-10 text-gray-400">
						<i class="fa-solid fa-magnifying-glass text-2xl mb-2"></i>
						<span class="text-sm">{m.commandPaletteNoResults()}</span>
						{#if searchText.trim()}
							<button
								class="mt-3 flex items-center gap-2 rounded-lg bg-violet-50 px-3 py-1.5 text-xs font-medium text-violet-600 hover:bg-violet-100 transition-colors cursor-pointer"
								onclick={() => {
									opened = false;
									goto(`/search?q=${encodeURIComponent(searchText.trim())}`, {
										label: 'search',
										breadcrumbAction: 'replace'
									});
								}}
							>
								<i class="fa-solid fa-arrow-right text-[10px]"></i>
								{m.commandPaletteSearchHint()}
							</button>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div
				class="flex items-center justify-between border-t border-gray-100 bg-gray-50/80 px-4 py-2 text-[11px] text-gray-400"
			>
				<div class="flex items-center gap-3">
					<span class="flex items-center gap-1">
						<kbd
							class="inline-flex items-center justify-center rounded border border-gray-200 bg-white px-1 py-0.5 font-mono text-[10px]"
							>↑</kbd
						>
						<kbd
							class="inline-flex items-center justify-center rounded border border-gray-200 bg-white px-1 py-0.5 font-mono text-[10px]"
							>↓</kbd
						>
						<span class="ml-0.5">{m.commandPaletteNavigate()}</span>
					</span>
					<span class="flex items-center gap-1">
						<kbd
							class="inline-flex items-center justify-center rounded border border-gray-200 bg-white px-1 py-0.5 font-mono text-[10px]"
							>↵</kbd
						>
						<span class="ml-0.5">{m.commandPaletteOpen()}</span>
					</span>
					<span class="flex items-center gap-1">
						<kbd
							class="inline-flex items-center justify-center rounded border border-gray-200 bg-white px-1 py-0.5 font-mono text-[10px]"
							>esc</kbd
						>
						<span class="ml-0.5">{m.close()}</span>
					</span>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	.animate-in {
		animation: palette-in 0.15s ease-out;
	}
	@keyframes palette-in {
		from {
			opacity: 0;
			transform: scale(0.98) translateY(-8px);
		}
		to {
			opacity: 1;
			transform: scale(1) translateY(0);
		}
	}
</style>
