<script lang="ts">
	import { safeTranslate } from '$lib/utils/i18n';
	import { AppBar, AppShell } from '@skeletonlabs/skeleton';
	import '../../app.postcss';

	import { browser } from '$app/environment';
	import Breadcrumbs from '$lib/components/Breadcrumbs/Breadcrumbs.svelte';
	import SideBar from '$lib/components/SideBar/SideBar.svelte';
	import { deleteCookie, getCookie } from '$lib/utils/cookies';
	import { clientSideToast, pageTitle } from '$lib/utils/stores';
	import * as m from '$paraglide/messages';
	import type { LayoutData } from './$types';

	export let data: LayoutData;

	let sidebarOpen = true;

	$: classesSidebarOpen = (open: boolean) => (open ? 'ml-64' : 'ml-7');

	$: if (browser) {
		const fromLogin = getCookie('from_login');
		if (fromLogin === 'true') {
			deleteCookie('from_login');
			fetch('/fe-api/waiting-risk-acceptances').then(async (res) => {
				const data = await res.json();
				const number = data.count ?? 0;
				if (number <= 0) return;
				clientSideToast.set({
					message: m.waitingRiskAcceptances({
						number: number,
						s: number > 1 ? 's' : '',
						itPlural: number > 1 ? 'i' : 'e'
					}),
					type: 'info'
				});
			});
		}
	}

	const licenseExpirationNotifyDays = data.LICENSE_EXPIRATION_NOTIFY_DAYS;
	const licenseStatus: Record<string, any> = data.licenseStatus;

	const licenseAboutToExpire =
		licenseStatus?.status === 'active' && licenseStatus?.days_left <= licenseExpirationNotifyDays;
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import type { PageData, ActionData } from './$types';
	import QuickStartModal from '$lib/components/SideBar/QuickStart/QuickStartModal.svelte';

	export let form: ActionData;
	const modalStore: ModalStore = getModalStore();
	function modalQuickStart(): void {
		let modalComponent: ModalComponent = {
			ref: QuickStartModal,
			props: {}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.quickStart()
		};
		modalStore.trigger(modal);
	}
</script>

<!-- App Shell -->
<AppShell
	slotPageContent="p-8 bg-gradient-to-br from-violet-100 to-slate-200"
	regionPage="transition-all duration-300 {classesSidebarOpen(sidebarOpen)}"
>
	<svelte:fragment slot="sidebarLeft">
		<SideBar bind:open={sidebarOpen} />
	</svelte:fragment>
	<svelte:fragment slot="pageHeader">
		{#if data.licenseStatus.status === 'expired'}
			<aside class="variant-soft-warning text-center w-full items-center py-2">
				{m.licenseExpiredMessage()}
			</aside>
		{:else if licenseAboutToExpire}
			<aside class="variant-soft-warning text-center w-full items-center py-2">
				{m.licenseAboutToExpireWarning({ days_left: licenseStatus.days_left })}
			</aside>
		{/if}
		<AppBar background="bg-white" padding="py-2 px-4" class="relative">
			<span
				class="text-2xl font-bold pb-1 bg-gradient-to-r from-pink-500 to-violet-600 bg-clip-text text-transparent"
				id="page-title"
			>
				{safeTranslate($pageTitle)}
			</span>
			{#if data?.user?.is_admin}
				<button
					on:click={modalQuickStart}
					class="absolute top-7 right-9 p-2 rounded-full bg-violet-500 text-white text-xs shadow-lg
                 ring-2 ring-violet-400 ring-offset-2 transition-all duration-300
                 hover:bg-violet-600 hover:ring-violet-300 hover:ring-offset-violet-100
                 hover:shadow-violet-500/50 focus:outline-none focus:ring-violet-500"
				>
					{m.quickStart()}
				</button>
			{/if}
			<hr class="w-screen my-1" />
			<Breadcrumbs />
		</AppBar>
	</svelte:fragment>
	<!-- Router Slot -->
	<slot />
	<!-- ---- / ---- -->
</AppShell>
