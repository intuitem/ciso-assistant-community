<script lang="ts">
	import { page } from '$app/state';
	import { LOCALE_MAP, language, defaultLangLabels } from '$lib/utils/locales';
	import { m } from '$paraglide/messages';
	import { getLocale, locales, setLocale } from '$paraglide/runtime';
	import { Popover } from '@skeletonlabs/skeleton-svelte';

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
</script>

<div class="border-t pt-2.5">
	<div class="flex flex-row items-center justify-between">
		<div class="flex flex-col w-3/4">
			{#if page.data.user}
				<span
					class="text-gray-900 text-sm whitespace-nowrap overflow-hidden truncate w-full"
					data-testid="sidebar-user-name-display"
				>
					{page.data.user.first_name}
					{page.data.user.last_name}
				</span>
				<span
					class="font-normal text-xs whitespace-nowrap truncate text-gray-600 mr-2 w-full"
					data-testid="sidebar-user-email-display"
				>
					{page.data.user.email}
				</span>
			{/if}
		</div>
		{#if enableMoreBtn}
			<Popover
				open={openState}
				onOpenChange={(e) => (openState = e.open)}
				positioning={{ placement: 'top' }}
				triggerBase="btn "
				contentBase="card whitespace-nowrap bg-white py-2 w-fit shadow-lg space-y-1"
				zIndex="1000"
			>
				{#snippet trigger()}
					<button class="btn bg-initial" data-testid="sidebar-more-btn" id="sidebar-more-btn">
						<i class="fa-solid fa-ellipsis-vertical"></i>
					</button>
				{/snippet}
				{#snippet content()}
					<div data-testid="sidebar-more-panel">
						<a
							href="/my-profile"
							onclick={(e) => {
								window.location.href = e.target.href;
							}}
							class="unstyled cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-gray-100 disabled:text-gray-500 text-gray-800"
							data-testid="profile-button"
							><i class="fa-solid fa-address-card mr-2"></i>{m.myProfile()}</a
						>
						<select
							{value}
							onchange={handleLocaleChange}
							class="border-y-white border-x-gray-100 focus:border-y-white focus:border-x-gray-100 w-full px-4 py-2.5 cursor-pointer block text-sm text-gray-800 bg-white focus:ring-0"
							data-testid="language-select"
						>
							{#each locales as lang}
								<option value={lang} selected={lang === getLocale()}>
									{defaultLangLabels[lang]} ({language[LOCALE_MAP[lang].name]})
								</option>
							{/each}
						</select>
						<button
							onclick={() => dispatch('triggerGT')}
							class="cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-gray-100 disabled:text-gray-500 text-gray-800"
							data-testid="gt-button"
							><i class="fa-solid fa-wand-magic-sparkles mr-2"></i>{m.guidedTour()}</button
						>
						<button
							onclick={() => dispatch('loadDemoDomain')}
							class="cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-gray-100 disabled:text-gray-500 text-gray-800"
							data-testid="load-demo-data-button"
							><i class="fa-solid fa-file-import mr-2"></i>{m.loadDemoData()}</button
						>
						<button
							onclick={modalBuildInfo}
							class="cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-gray-100 disabled:text-gray-500 text-gray-800"
							data-testid="about-button"
							><i class="fa-solid fa-circle-info mr-2"></i>{m.aboutCiso()}</button
						>
						<a
							href="https://intuitem.gitbook.io/ciso-assistant"
							target="_blank"
							class="unstyled cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-gray-100 disabled:text-gray-500 text-gray-800"
							data-testid="docs-button"><i class="fa-solid fa-book mr-2"></i>{m.onlineDocs()}</a
						>
						<form action="/logout" method="POST">
							<button class="w-full" type="submit" data-testid="logout-button">
								<span
									class="flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-gray-100 disabled:text-gray-500 text-gray-800"
									><i class="fa-solid fa-right-from-bracket mr-2"></i>{m.Logout()}</span
								>
							</button>
						</form>
					</div>
				{/snippet}
			</Popover>
		{:else}
			<button
				class="btn bg-initial"
				data-testid="sidebar-more-btn-disabled"
				id="sidebar-more-btn-disabled"><i class="fa-solid fa-ellipsis-vertical"></i></button
			>
		{/if}
	</div>
</div>
