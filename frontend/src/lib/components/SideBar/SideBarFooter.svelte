<script lang="ts">
	import { page } from '$app/state';
	import { LOCALE_MAP, language, defaultLangLabels } from '$lib/utils/locales';
	import { m } from '$paraglide/messages';
	import { getLocale, locales, setLocale } from '$paraglide/runtime';
	import ThemeSwitch from '$lib/components/ThemeSwitch/ThemeSwitch.svelte';

	import { getModalStore, type ModalSettings } from '$lib/components/Modals/stores';
	import { createEventDispatcher, onMount } from 'svelte';
	const dispatch = createEventDispatcher();

	const modalStore = getModalStore();

	let value = $state(getLocale());
	async function handleLocaleChange(event: Event) {
		value = event?.target?.value;
		await fetch('/fe-api/user-preferences', {
			method: 'PATCH',
			body: JSON.stringify({
				lang: value
			})
		}).then(() => setLocale(value));
	}

	async function modalBuildInfo() {
		const res = await fetch('/fe-api/build').then((res) => res.json());
		const modal: ModalSettings = {
			type: 'component',
			component: 'displayJSONModal',
			title: m.aboutCiso(),
			body: JSON.stringify(res)
		};
		openState = false;
		modalStore.trigger(modal);
	}

	let enableMoreBtn = $state(false);

	onMount(() => {
		enableMoreBtn = true;
	});

	let openState = $state(false);
	let triggerEl: HTMLButtonElement | undefined = $state();
	let menuStyle = $derived.by(() => {
		if (!openState || !triggerEl) return '';
		const rect = triggerEl.getBoundingClientRect();
		const centerX = rect.left + rect.width / 2;
		return `position: fixed; bottom: ${window.innerHeight - rect.top + 8}px; left: ${centerX}px; transform: translateX(-50%);`;
	});
</script>

<div class="border-t pt-2.5">
	<div class="flex flex-row items-center justify-between">
		<div class="flex flex-col w-3/4">
			{#if page.data.user}
				<span
					class="text-surface-950-50 text-sm whitespace-nowrap overflow-hidden truncate w-full"
					data-testid="sidebar-user-name-display"
				>
					{page.data.user.first_name}
					{page.data.user.last_name}
				</span>
				<span
					class="font-normal text-xs whitespace-nowrap truncate text-surface-600-400 mr-2 w-full"
					data-testid="sidebar-user-email-display"
				>
					{page.data.user.email}
				</span>
			{/if}
		</div>
		{#if enableMoreBtn}
			<div class="relative">
				<button
					bind:this={triggerEl}
					class="btn bg-initial"
					data-testid="sidebar-more-btn"
					aria-label="More options"
					id="sidebar-more-btn"
					onclick={() => (openState = !openState)}
				>
					<i class="fa-solid fa-ellipsis-vertical"></i>
				</button>
				{#if openState}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div
						class="fixed inset-0 z-[999]"
						onclick={() => (openState = false)}
						onkeydown={(e) => e.key === 'Escape' && (openState = false)}
					></div>
					<div
						style={menuStyle}
						class="z-[1000] card whitespace-nowrap bg-surface-50-950 py-2 w-fit shadow-lg space-y-1 rounded-lg"
						data-testid="sidebar-more-panel"
					>
						<a
							href="/my-profile"
							onclick={() => {
								openState = false;
							}}
							class="unstyled cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-surface-200-800 disabled:text-surface-400-600 text-surface-950-50"
							data-testid="profile-button"
							><i class="fa-solid fa-address-card mr-2"></i>{m.myProfile()}</a
						>
						<select
							{value}
							onchange={handleLocaleChange}
							class="border-y-transparent border-x-surface-100-900 focus:border-y-transparent focus:border-x-surface-100-900 w-full px-4 py-2.5 cursor-pointer block text-sm text-surface-950-50 bg-surface-50-950 focus:ring-0"
							data-testid="language-select"
						>
							{#each locales as lang}
								<option value={lang} selected={lang === getLocale()}>
									{defaultLangLabels[lang]} ({language[LOCALE_MAP[lang].name]})
								</option>
							{/each}
						</select>
						<ThemeSwitch />
						<button
							onclick={() => {
								openState = false;
								dispatch('triggerGT');
							}}
							class="cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-surface-200-800 disabled:text-surface-400-600 text-surface-950-50"
							data-testid="gt-button"
							><i class="fa-solid fa-wand-magic-sparkles mr-2"></i>{m.guidedTour()}</button
						>
						<button
							onclick={() => {
								openState = false;
								dispatch('loadDemoDomain');
							}}
							class="cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-surface-200-800 disabled:text-surface-400-600 text-surface-950-50"
							data-testid="load-demo-data-button"
							><i class="fa-solid fa-file-import mr-2"></i>{m.loadDemoData()}</button
						>
						<button
							onclick={() => {
								openState = false;
								modalBuildInfo();
							}}
							class="cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-surface-200-800 disabled:text-surface-400-600 text-surface-950-50"
							data-testid="about-button"
							><i class="fa-solid fa-circle-info mr-2"></i>{m.aboutCiso()}</button
						>
						<a
							href="https://intuitem.gitbook.io/ciso-assistant"
							target="_blank"
							class="unstyled cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-surface-200-800 disabled:text-surface-400-600 text-surface-950-50"
							data-testid="docs-button"><i class="fa-solid fa-book mr-2"></i>{m.onlineDocs()}</a
						>
						<form action="/logout" method="POST">
							<button class="w-full" type="submit" data-testid="logout-button">
								<span
									class="flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-surface-200-800 disabled:text-surface-400-600 text-surface-950-50"
									><i class="fa-solid fa-right-from-bracket mr-2"></i>{m.Logout()}</span
								>
							</button>
						</form>
					</div>
				{/if}
			</div>
		{:else}
			<button
				class="btn bg-initial"
				data-testid="sidebar-more-btn-disabled"
				aria-label="More options"
				id="sidebar-more-btn-disabled"><i class="fa-solid fa-ellipsis-vertical"></i></button
			>
		{/if}
	</div>
</div>
