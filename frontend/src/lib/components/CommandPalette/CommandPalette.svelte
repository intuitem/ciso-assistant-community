<script lang="ts">
	import { browser } from '$app/environment';
	import { safeTranslate } from '$lib/utils/i18n';
	import { goto } from '$lib/utils/breadcrumbs';
	import { page } from '$app/state';
	import {
		expandChat,
		getIsStreaming,
		sendMessage,
		setInputText
	} from '../ChatWidget/chatStore.svelte';
	import { m } from '$paraglide/messages';
	import { createIntentHref } from '$lib/utils/create-intent';
	import {
		awaitingArgument,
		buildCreateCommands,
		buildNavigationCommands,
		matchCommands,
		type PaletteCommand,
		type PaletteGroup
	} from './commands';

	let opened = $state(false);
	let searchInput: HTMLElement | null = $state(null);

	const featureFlags = $derived(page.data?.featureflags ?? {});

	const navigationCommands = $derived(buildNavigationCommands(page.data?.user, featureFlags));
	const createCommands = $derived(buildCreateCommands(page.data?.user, featureFlags));

	const actionCommands: PaletteCommand[] = $derived([
		{
			label: safeTranslate('search'),
			group: 'action' as const,
			icon: 'fa-solid fa-magnifying-glass',
			keywords: [m.commandKeywordSearch(), 'search'],
			run: (argument: string) => runSearch(argument)
		},
		...(featureFlags.chat_mode
			? [
					{
						label: safeTranslate('askAi'),
						group: 'action' as const,
						icon: 'fa-solid fa-wand-magic-sparkles',
						keywords: [m.commandKeywordAsk(), 'ask'],
						run: askAi
					},
					{
						label: safeTranslate('openAssistant'),
						group: 'action' as const,
						icon: 'fa-solid fa-robot',
						run: expandChat
					}
				]
			: [])
	]);

	let selected = $state(0);
	let searchText = $state('');

	// `+` to make something, `/` to do something. Kept apart so the create list does not
	// bury the verbs.
	type PaletteMode = 'create' | 'action' | 'search';

	function modeFor(sigil: string | undefined): PaletteMode {
		if (sigil === '+') return 'create';
		if (sigil === '/') return 'action';
		return 'search';
	}

	const mode = $derived(modeFor(searchText[0]));
	const query = $derived(mode === 'search' ? searchText : searchText.slice(1));

	const pool = $derived(
		mode === 'create'
			? createCommands
			: mode === 'action'
				? actionCommands
				: [...navigationCommands, ...actionCommands]
	);

	const match = $derived(matchCommands(pool, query));
	const items = $derived(match.items);
	const argument = $derived(match.argument);
	const verbCommand = $derived(match.verbCommand);

	const MODE_ICONS: Record<PaletteMode, string> = {
		create: 'fa-plus',
		action: 'fa-terminal',
		search: 'fa-magnifying-glass'
	};

	const GROUP_LABELS: Record<PaletteGroup, () => string> = {
		navigation: m.commandPaletteNavigation,
		create: m.commandPaletteCreate,
		action: m.commandPaletteActions
	};

	$effect(() => {
		if (selected >= items.length) {
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

	function execute(command: PaletteCommand) {
		if (awaitingArgument(command, argument)) {
			// Commit the verb instead of firing; the palette stays open for the argument.
			searchText = `/${command.keywords![0]} `;
			selected = 0;
			return;
		}
		opened = false;
		if (command.run) return command.run(argument.trim());
		if (!command.href) return;
		goto(command.opensCreateForm ? createIntentHref(command.href) : command.href, {
			label: command.breadcrumb ?? command.label,
			breadcrumbAction: 'replace'
		});
	}

	function askAi(question: string) {
		expandChat();
		// `streamResponse` aborts whatever is in flight, so sending now would cut off an
		// answer mid-sentence. Hand it to the composer instead.
		if (getIsStreaming()) return setInputText(question);
		sendMessage(question);
	}

	function runSearch(text: string) {
		opened = false;
		goto(`/search?q=${encodeURIComponent(text.trim())}`, {
			label: 'search',
			breadcrumbAction: 'replace'
		});
	}

	function scrollToSelected() {
		document.querySelector(`[data-cmdk-index="${selected}"]`)?.scrollIntoView({ block: 'nearest' });
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
			if (selected < items.length - 1) {
				selected++;
			}
			scrollToSelected();
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			if (selected > 0) {
				selected--;
			}
			scrollToSelected();
		} else if (e.key === 'Enter') {
			if (selected < items.length) {
				execute(items[selected]);
			} else if (mode === 'search' && searchText.trim()) {
				// No match — launch universal search
				runSearch(searchText);
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
			class="w-full max-w-lg mx-4 overflow-hidden rounded-xl bg-surface-50-950 shadow-2xl ring-1 ring-black/10 animate-in"
		>
			<!-- Search input -->
			<div class="flex items-center gap-3 px-4 border-b border-surface-200-800">
				<i class="fa-solid {MODE_ICONS[mode]} text-surface-400-600 text-sm"></i>
				<input
					class="w-full bg-transparent py-3.5 text-sm text-surface-900-100 placeholder-surface-400-600 outline-none border-none ring-0 focus:outline-none focus:border-none focus:ring-0 shadow-none"
					type="text"
					bind:value={searchText}
					bind:this={searchInput}
					placeholder={m.searchPagesAndObjects()}
				/>
				<button
					onclick={() => (opened = false)}
					class="shrink-0 rounded-md border border-surface-200-800 bg-surface-100-900 px-1.5 py-0.5 text-[10px] font-medium text-surface-600-400 hover:bg-surface-200-800 cursor-pointer"
				>
					ESC
				</button>
			</div>

			<!-- Results -->
			<div class="max-h-72 overflow-y-auto overscroll-contain">
				{#if items.length > 0}
					<div class="px-2 pb-2">
						{#each items as item, index (`${item.group}:${item.href ?? item.label}`)}
							{@const startsGroup = index === 0 || items[index - 1].group !== item.group}
							{#if startsGroup}
								<div class="px-3 py-2">
									<span
										class="text-[11px] font-semibold uppercase tracking-wider text-surface-400-600 px-1"
										>{GROUP_LABELS[item.group]()}</span
									>
								</div>
							{/if}
							<button
								class="w-full flex items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors cursor-pointer
									{selected === index
									? 'bg-violet-50 text-violet-900'
									: 'text-surface-700-300 hover:bg-surface-100-900'}"
								data-cmdk-index={index}
								onmouseenter={() => {
									selected = index;
								}}
								onclick={() => execute(item)}
							>
								{#if item.icon}
									<i
										class="{item.icon} w-4 text-center text-xs {selected === index
											? 'text-violet-500'
											: 'text-surface-400-600'}"
									></i>
								{/if}
								<span class="shrink-0">{item.label}</span>
								{#if item === verbCommand && argument.trim()}
									<span
										class="min-w-0 flex-1 truncate rounded bg-violet-100 px-1.5 py-0.5 text-[11px] text-violet-700"
										>{argument}</span
									>
								{:else if awaitingArgument(item, argument)}
									<span class="min-w-0 flex-1 truncate text-[11px] text-surface-400-600 italic"
										>{m.commandPaletteArgumentHint()}</span
									>
								{:else}
									<span class="min-w-0 flex-1"></span>
								{/if}
								{#if selected === index}
									<span class="text-[10px] text-violet-400">↵</span>
								{/if}
							</button>
						{/each}
					</div>
				{:else}
					<div class="flex flex-col items-center justify-center py-10 text-surface-400-600">
						<i class="fa-solid fa-magnifying-glass text-2xl mb-2"></i>
						<span class="text-sm">{m.commandPaletteNoResults()}</span>
						{#if mode === 'search' && searchText.trim()}
							<button
								class="mt-3 flex items-center gap-2 rounded-lg bg-violet-50 px-3 py-1.5 text-xs font-medium text-violet-600 hover:bg-violet-100 transition-colors cursor-pointer"
								onclick={() => runSearch(searchText)}
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
				class="flex items-center justify-between border-t border-surface-100-900 bg-surface-100-900/80 px-4 py-2 text-[11px] text-surface-400-600"
			>
				<div class="flex items-center gap-3">
					<span class="flex items-center gap-1">
						<kbd
							class="inline-flex items-center justify-center rounded border border-surface-200-800 bg-surface-50-950 px-1 py-0.5 font-mono text-[10px]"
							>↑</kbd
						>
						<kbd
							class="inline-flex items-center justify-center rounded border border-surface-200-800 bg-surface-50-950 px-1 py-0.5 font-mono text-[10px]"
							>↓</kbd
						>
						<span class="ml-0.5">{m.commandPaletteNavigate()}</span>
					</span>
					<span class="flex items-center gap-1">
						<kbd
							class="inline-flex items-center justify-center rounded border border-surface-200-800 bg-surface-50-950 px-1 py-0.5 font-mono text-[10px]"
							>↵</kbd
						>
						<span class="ml-0.5">{m.commandPaletteOpen()}</span>
					</span>
				</div>
				<div class="flex items-center gap-3">
					<span class="flex items-center gap-1">
						<kbd
							class="inline-flex items-center justify-center rounded border border-surface-200-800 bg-surface-50-950 px-1 py-0.5 font-mono text-[10px]"
							>+</kbd
						>
						<span class="ml-0.5">{m.commandPaletteCreateHint()}</span>
					</span>
					<span class="flex items-center gap-1">
						<kbd
							class="inline-flex items-center justify-center rounded border border-surface-200-800 bg-surface-50-950 px-1 py-0.5 font-mono text-[10px]"
							>/</kbd
						>
						<span class="ml-0.5">{m.commandPaletteCommandHint()}</span>
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
