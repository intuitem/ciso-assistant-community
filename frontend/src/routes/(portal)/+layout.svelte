<script lang="ts">
	import '../../app.css';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import { m } from '$paraglide/messages';
	import CommandPalette from '$lib/components/CommandPalette/CommandPalette.svelte';
	import ThemeToggle from '$lib/components/ThemeToggle/ThemeToggle.svelte';
	import { initThemeFromUser } from '$lib/utils/theme';
	import type { LayoutData } from './$types';

	let { data, children }: { data: LayoutData; children?: import('svelte').Snippet } = $props();

	const isMac = browser && navigator.platform.toUpperCase().indexOf('MAC') >= 0;
	const modifierKey = isMac ? '⌘' : 'Ctrl';

	let commandPalette: ReturnType<typeof CommandPalette> | undefined = $state();
	let menuOpen = $state(false);
	let switcherOpen = $state(false);

	const current = $derived(data.portals.find((p) => p.id === $page.params.id));

	// Admins-only nudge: personal folders enabled but no parent set, so "My space" is off.
	const personalFoldersMisconfigured = $derived(
		!!data.user?.is_admin &&
			!!data.featureflags?.personal_folders &&
			!data.settings?.personal_folders_parent
	);

	onMount(() => initThemeFromUser(data.user?.preferences));
</script>

<div class="min-h-screen bg-linear-to-br from-surface-100-900 to-surface-200-800">
	<header
		class="sticky top-0 z-50 flex items-center justify-between border-b border-surface-200-800 bg-surface-50-950/80 px-6 py-3 backdrop-blur"
	>
		<div class="flex items-center gap-3">
			<!-- Brand mark: overridable on the PRO plan (branding) -->
			<img src="/favicon.ico" alt="" class="h-7 w-7" />
			<!-- Portal switcher -->
			<div class="relative">
				<button
					onclick={() => (switcherOpen = !switcherOpen)}
					class="flex items-center gap-2 rounded-lg px-2 py-1 text-lg font-bold text-surface-900-100 hover:bg-surface-100-900 cursor-pointer"
				>
					{current?.name ?? m.portals()}
					<i class="fa-solid fa-chevron-down text-xs text-surface-400"></i>
				</button>
				{#if switcherOpen}
					<div
						class="absolute left-0 mt-2 w-56 rounded-lg border border-surface-200-800 bg-surface-50-950 p-2 shadow-xl"
					>
						{#each data.portals as p}
							<a
								href="/portal/{p.id}"
								onclick={() => (switcherOpen = false)}
								class="flex items-center justify-between rounded px-2 py-1.5 text-sm hover:bg-surface-100-900 {p.id ===
								current?.id
									? 'font-semibold text-violet-600'
									: ''}"
							>
								{p.name}
								{#if p.id === current?.id}<i class="fa-solid fa-check text-xs"></i>{/if}
							</a>
						{/each}
						{#if data.user?.is_admin}
							<a
								href="/portal-editor"
								onclick={() => (switcherOpen = false)}
								class="mt-1 flex items-center gap-2 border-t border-surface-200-800 px-2 pt-2 text-sm text-surface-500 hover:text-primary-500"
							>
								<i class="fa-solid fa-sliders text-xs"></i>{m.managePortals()}
							</a>
						{/if}
					</div>
				{/if}
			</div>
		</div>
		<div class="flex items-center gap-2">
			<ThemeToggle />
			{#if !data?.user?.is_third_party}
				<button
					onclick={() => commandPalette?.toggle()}
					class="flex items-center gap-2 rounded-lg border border-surface-200-800 bg-surface-100-900/80 px-3 py-1.5 text-xs text-surface-500 hover:bg-surface-200-800 cursor-pointer"
				>
					<i class="fa-solid fa-magnifying-glass"></i>
					<span class="hidden sm:inline">{m.searchEllipsis()}</span>
					<kbd
						class="hidden sm:inline rounded border border-surface-200-800 px-1.5 py-0.5 font-mono text-[10px]"
						>{modifierKey}K</kbd
					>
				</button>
			{/if}
			<a
				href="/analytics"
				class="rounded-lg border border-surface-200-800 px-3 py-1.5 text-xs text-surface-600-400 hover:bg-surface-200-800"
			>
				<i class="fa-solid fa-arrow-right-from-bracket mr-1"></i>{m.backToApp()}
			</a>
			<div class="relative">
				<button
					onclick={() => (menuOpen = !menuOpen)}
					class="flex h-9 w-9 items-center justify-center rounded-full bg-violet-500 text-sm font-semibold text-white cursor-pointer"
				>
					{(data.user?.first_name?.[0] ?? data.user?.email?.[0] ?? '?').toUpperCase()}
				</button>
				{#if menuOpen}
					<div
						class="absolute right-0 mt-2 w-48 rounded-lg border border-surface-200-800 bg-surface-50-950 p-2 shadow-xl"
					>
						<div class="px-2 py-1 text-xs text-surface-500 truncate">{data.user?.email}</div>
						<a href="/my-profile" class="block rounded px-2 py-1.5 text-sm hover:bg-surface-100-900"
							>{m.myProfile()}</a
						>
						<form action="/logout" method="POST">
							<button
								class="block w-full rounded px-2 py-1.5 text-left text-sm hover:bg-surface-100-900 cursor-pointer"
								>{m.Logout()}</button
							>
						</form>
					</div>
				{/if}
			</div>
		</div>
	</header>

	{#if !data?.user?.is_third_party}
		<CommandPalette bind:this={commandPalette} />
	{/if}

	<main class="mx-auto max-w-6xl px-6 py-10">
		{#if personalFoldersMisconfigured}
			<aside class="card preset-tonal-warning mb-6 p-4 text-sm">
				<i class="fa-solid fa-triangle-exclamation mr-2"></i>{m.personalFoldersParentNotSet()}
			</aside>
		{/if}
		{@render children?.()}
	</main>
</div>
