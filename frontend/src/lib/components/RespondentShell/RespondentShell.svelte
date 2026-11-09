<script lang="ts">
	import { page } from '$app/state';
	import { m } from '#paraglide/messages.js';
	import { getLocale, locales, setLocale } from '#paraglide/runtime.js';
	import { LOCALE_MAP, language, defaultLangLabels } from '#lib/utils/locales.js';
	import Logo from '#lib/components/Logo/Logo.svelte';
	import ThemeToggle from '#lib/components/ThemeToggle/ThemeToggle.svelte';

	let { title, children }: { title: string; children?: import('svelte').Snippet } = $props();

	const user = $derived(page.data.user);
	let menuOpen = $state(false);
	let menu: HTMLDivElement | undefined = $state();

	async function changeLocale(event: Event) {
		const lang = (event.target as HTMLSelectElement).value;
		await fetch('/fe-api/user-preferences', {
			method: 'PATCH',
			body: JSON.stringify({ lang })
		});
		setLocale(lang as ReturnType<typeof getLocale>);
	}
</script>

<svelte:window
	onclick={(e) => {
		if (menuOpen && !menu?.contains(e.target as Node)) menuOpen = false;
	}}
	onkeydown={(e) => {
		if (e.key === 'Escape') menuOpen = false;
	}}
/>

<div class="min-h-dvh bg-linear-to-br from-surface-100-900 to-surface-200-800">
	<header
		class="sticky top-0 z-50 flex flex-wrap items-center justify-between gap-4 border-b border-surface-200-800 bg-surface-50-950 px-4 py-3 sm:px-6"
	>
		<div class="flex items-center gap-6">
			<a
				href="/auditee-dashboard"
				class="flex items-center [&_img]:h-8 [&_img]:w-auto"
				aria-label={m.myQuestionnaires()}
			>
				<Logo />
			</a>
			<a
				href="/auditee-dashboard"
				class="text-sm font-semibold text-surface-700-300 hover:text-primary-500"
				data-testid="respondent-home"
			>
				{m.myQuestionnaires()}
			</a>
		</div>
		<div class="flex items-center gap-2">
			<select
				value={getLocale()}
				onchange={changeLocale}
				aria-label={m.language()}
				class="select w-auto max-w-36 py-1 text-xs sm:max-w-none"
				data-testid="language-select"
			>
				{#each locales as lang}
					<option value={lang}>{defaultLangLabels[lang]} ({language[LOCALE_MAP[lang].name]})</option
					>
				{/each}
			</select>
			<ThemeToggle />
			<div class="relative" bind:this={menu}>
				<button
					onclick={() => (menuOpen = !menuOpen)}
					aria-label={m.myProfile()}
					class="flex h-9 w-9 items-center justify-center rounded-full bg-violet-500 text-sm font-semibold text-white cursor-pointer"
					data-testid="respondent-avatar"
				>
					{(user?.first_name?.[0] ?? user?.email?.[0] ?? '?').toUpperCase()}
				</button>
				{#if menuOpen}
					<div
						class="absolute right-0 mt-2 w-56 rounded-lg border border-surface-200-800 bg-surface-50-950 p-2 shadow-xl"
					>
						<div class="truncate px-2 py-1 text-xs text-surface-500">{user?.email}</div>
						<a
							href="/my-profile"
							onclick={() => (menuOpen = false)}
							class="block rounded px-2 py-1.5 text-sm hover:bg-surface-100-900">{m.myProfile()}</a
						>
						<form action="/logout" method="POST">
							<button
								class="block w-full rounded px-2 py-1.5 text-left text-sm hover:bg-surface-100-900 cursor-pointer"
								data-testid="logout-button">{m.Logout()}</button
							>
						</form>
					</div>
				{/if}
			</div>
		</div>
	</header>
	<main class="mx-auto max-w-7xl px-4 py-8 sm:px-6">
		<h1
			class="pb-6 text-2xl font-bold bg-linear-to-r from-pink-500 to-violet-600 bg-clip-text text-transparent"
			id="page-title"
		>
			{title}
		</h1>
		{@render children?.()}
	</main>
</div>
