<script lang="ts">
	import { page } from '$app/stores';
	import { popup } from '@skeletonlabs/skeleton';
	import type { ModalSettings, PopupSettings } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import { locales, getLocale, setLocale } from '$paraglide/runtime';
	import { LOCALE_MAP } from '$lib/utils/locales';
	import { m } from '$paraglide/messages';
	import { setCookie } from '$lib/utils/cookies';

	import { createEventDispatcher, onMount } from 'svelte';
	const dispatch = createEventDispatcher();

	const language: any = {
		french: m.french(),
		english: m.english(),
		arabic: m.arabic(),
		portuguese: m.portuguese(),
		spanish: m.spanish(),
		german: m.german(),
		dutch: m.dutch(),
		italian: m.italian(),
		polish: m.polish(),
		romanian: m.romanian(),
		hindi: m.hindi(),
		urdu: m.urdu(),
		czech: m.czech(),
		swedish: m.swedish(),
		indonesian: m.indonesian(),
		danish: m.danish(),
		hungarian: m.hungarian()
	};

	const modalStore = getModalStore();

	const defaultLangLabels = {
		fr: 'Français',
		en: 'English',
		ar: 'العربية',
		pt: 'Português',
		es: 'Español',
		nl: 'Nederlands',
		de: 'Deutsch',
		it: 'Italiano',
		pl: 'Polski',
		ro: 'Română',
		hi: 'हिंदी',
		ur: 'اردو',
		cs: 'Český',
		sv: 'Svenska',
		id: 'Bahasa Indonesia',
		da: 'Dansk',
		hu: 'Magyar'
	};

	let value = getLocale();
	async function handleLocaleChange(event: Event) {
		event.preventDefault();
		value = event?.target?.value;
		setLocale(value);
		fetch('/fe-api/user-preferences', {
			method: 'PATCH',
			body: JSON.stringify({
				lang: value
			})
		});
		// sessionStorage.setItem('lang', value);
		setCookie('PARAGLIDE_LOCALE', value);
		window.location.reload();
	}

	const popupUser: PopupSettings = {
		event: 'click',
		target: 'popupUser',
		placement: 'top'
	};

	async function modalBuildInfo() {
		const res = await fetch('/fe-api/build').then((res) => res.json());
		const modal: ModalSettings = {
			type: 'component',
			component: 'displayJSONModal',
			title: 'About CISO Assistant',
			body: JSON.stringify(res)
		};
		modalStore.trigger(modal);
	}

	let enableMoreBtn = false;

	onMount(() => {
		enableMoreBtn = true;
	});
</script>

<div class="border-t pt-2.5">
	<div class="flex flex-row items-center justify-between">
		<div class="flex flex-col w-3/4">
			{#if $page.data.user}
				<span
					class="text-gray-900 text-sm whitespace-nowrap overflow-hidden truncate w-full"
					data-testid="sidebar-user-name-display"
				>
					{$page.data.user.first_name}
					{$page.data.user.last_name}
				</span>
				<span
					class="font-normal text-xs whitespace-nowrap truncate text-gray-600 mr-2 w-full"
					data-testid="sidebar-user-email-display"
				>
					{$page.data.user.email}
				</span>
			{/if}
		</div>
		{#key $modalStore}
			{#if enableMoreBtn}
				<button
					class="btn bg-initial"
					data-testid="sidebar-more-btn"
					id="sidebar-more-btn"
					use:popup={popupUser}><i class="fa-solid fa-ellipsis-vertical" /></button
				>
			{:else}
				<button
					class="btn bg-initial"
					data-testid="sidebar-more-btn-disabled"
					id="sidebar-more-btn-disabled"><i class="fa-solid fa-ellipsis-vertical" /></button
				>
			{/if}
		{/key}
		<div
			class="card whitespace-nowrap bg-white py-2 w-fit shadow-lg space-y-1"
			data-testid="sidebar-more-panel"
			data-popup="popupUser"
		>
			<a
				href="/my-profile"
				on:click={(e) => {
					window.location.href = e.target.href;
				}}
				class="unstyled cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-gray-100 disabled:text-gray-500 text-gray-800"
				data-testid="profile-button"><i class="fa-solid fa-address-card mr-2" />{m.myProfile()}</a
			>
			<select
				{value}
				on:change={handleLocaleChange}
				class="border-y-white border-x-gray-100 focus:border-y-white focus:border-x-gray-100 w-full cursor-pointer block text-sm text-gray-800 bg-white focus:ring-0"
				data-testid="language-select"
			>
				{#each locales as lang}
					<option value={lang} selected={lang === getLocale()}>
						{defaultLangLabels[lang]} ({language[LOCALE_MAP[lang].name]})
					</option>
				{/each}
			</select>
			<button
				on:click={() => dispatch('triggerGT')}
				class="cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-gray-100 disabled:text-gray-500 text-gray-800"
				data-testid="gt-button"
				><i class="fa-solid fa-wand-magic-sparkles mr-2" />{m.guidedTour()}</button
			>
			<button
				on:click={() => dispatch('loadDemoDomain')}
				class="cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-gray-100 disabled:text-gray-500 text-gray-800"
				data-testid="load-demo-data-button"
				><i class="fa-solid fa-file-import mr-2" />{m.loadDemoData()}</button
			>
			<button
				on:click={modalBuildInfo}
				class="cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-gray-100 disabled:text-gray-500 text-gray-800"
				data-testid="about-button"><i class="fa-solid fa-circle-info mr-2" />{m.aboutCiso()}</button
			>
			<a
				href="https://intuitem.gitbook.io/ciso-assistant"
				target="_blank"
				class="unstyled cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-gray-100 disabled:text-gray-500 text-gray-800"
				data-testid="docs-button"><i class="fa-solid fa-book mr-2" />{m.onlineDocs()}</a
			>
			<form action="/logout" method="POST">
				<button class="w-full" type="submit" data-testid="logout-button">
					<span
						class="flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-gray-100 disabled:text-gray-500 text-gray-800"
						><i class="fa-solid fa-right-from-bracket mr-2" />{m.Logout()}</span
					>
				</button>
			</form>
		</div>
	</div>
</div>
