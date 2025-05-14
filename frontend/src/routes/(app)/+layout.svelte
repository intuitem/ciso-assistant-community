<script lang="ts">
	import { run } from 'svelte/legacy';

	// Most of your app wide CSS should be put in this file
	import '../../app.css';
	import { AppBar } from '@skeletonlabs/skeleton-svelte';
	import { safeTranslate } from '$lib/utils/i18n';

	import SideBar from '$lib/components/SideBar/SideBar.svelte';
	import Breadcrumbs from '$lib/components/Breadcrumbs/Breadcrumbs.svelte';
	import { pageTitle, clientSideToast } from '$lib/utils/stores';
	import { getCookie, deleteCookie } from '$lib/utils/cookies';
	import { browser } from '$app/environment';
	import { m } from '$paraglide/messages';

	import CommandPalette from '$lib/components/CommandPalette/CommandPalette.svelte';

	let sidebarOpen = $state(true);

	let classesSidebarOpen = $derived((open: boolean) => (open ? 'ml-7 lg:ml-64' : 'ml-7'));

	run(() => {
		if (browser) {
			const fromLogin = getCookie('from_login');
			if (fromLogin === 'true') {
				deleteCookie('from_login');
				fetch('/fe-api/waiting-risk-acceptances').then(async (res) => {
					const data = await res.json();
					const number = data.count ?? 0;
					if (number <= 0) return;
					// clientSideToast.set({
					// 	message: m.waitingRiskAcceptances({
					// 		number: number,
					// 		s: number > 1 ? 's' : '',
					// 		itPlural: number > 1 ? 'i' : 'e'
					// 	}),
					// 	type: 'info'
					// });
				});
			}
		}
	});
	// import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton-svelte';
	import type { PageData, ActionData } from './$types';
	// import QuickStartModal from '$lib/components/SideBar/QuickStart/QuickStartModal.svelte';

	import { getSidebarVisibleItems } from '$lib/utils/sidebar-config';

	interface Props {
		data: PageData;
		form: ActionData;
		sideBarVisibleItems?: any;
		children?: import('svelte').Snippet;
	}

	let {
		data,
		form,
		sideBarVisibleItems = getSidebarVisibleItems(data?.featureflags),
		children
	}: Props = $props();

	// const modalStore: ModalStore = getModalStore();
	// function modalQuickStart(): void {
	// 	let modalComponent: ModalComponent = {
	// 		ref: QuickStartModal,
	// 		props: {}
	// 	};
	// 	let modal: ModalSettings = {
	// 		type: 'component',
	// 		component: modalComponent,
	// 		// Data
	// 		title: m.quickStart()
	// 	};
	// 	modalStore.trigger(modal);
	// }
</script>

<!-- App Shell -->
<AppShell
	slotPageContent="p-8 bg-linear-to-br from-violet-100 to-slate-200"
	regionPage="transition-all duration-300 {classesSidebarOpen(sidebarOpen)}"
>
	{#snippet sidebarLeft()}
		<SideBar bind:open={sidebarOpen} {sideBarVisibleItems} />
	{/snippet}
	{#snippet pageHeader()}
		<AppBar background="bg-white" padding="py-2 px-4" class="relative">
			<span
				class="text-2xl font-bold pb-1 bg-linear-to-r from-pink-500 to-violet-600 bg-clip-text text-transparent"
				id="page-title"
			>
				{safeTranslate($pageTitle)}
			</span>
			{#if data?.user?.is_admin}
				<button <!-- onclick={modalQuickStart} -->
					class="absolute top-7 right-9 p-2 rounded-full bg-violet-500 text-white text-xs shadow-lg
					ring-2 ring-violet-400 ring-offset-2 transition-all duration-300 hover:bg-violet-600
					hover:ring-violet-300 hover:ring-offset-violet-100 hover:shadow-violet-500/50
					focus:outline-hidden focus:ring-violet-500" >
					{m.quickStart()}
				</button>
			{/if}
			<hr class="w-screen my-1" />
			<Breadcrumbs />
		</AppBar>
	{/snippet}
	<!-- Router Slot -->
	<CommandPalette />
	{@render children?.()}
	<!-- ---- / ---- -->
</AppShell>
