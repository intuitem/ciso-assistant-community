<script lang="ts">
	// Most of your app wide CSS should be put in this file
	import '../../app.postcss';
	import { AppShell, AppBar } from '@skeletonlabs/skeleton';
	import { safeTranslate } from '$lib/utils/i18n';

	import SideBar from '$lib/components/SideBar/SideBar.svelte';
	import Breadcrumbs from '$lib/components/Breadcrumbs/Breadcrumbs.svelte';
	import { pageTitle, clientSideToast } from '$lib/utils/stores';
	import { getCookie, deleteCookie } from '$lib/utils/cookies';
	import { browser } from '$app/environment';
	import * as m from '$paraglide/messages';

	let sidebarOpen = true;

	$: classesSidebarOpen = (open: boolean) => (open ? 'ml-64' : 'ml-7');

	$: if (browser) {
		const fromLogin = getCookie("from_login");
		if (fromLogin === "true" || true) {
			deleteCookie("from_login");
			fetch("/api/waiting-risk-acceptances").then(async (res) => {
				const data = await res.json();
				const number = data.count ?? 0;
				if (number <= 0)
					return;
				clientSideToast.set({
					message: m.waitingRiskAcceptances({
						number: number,
						s: number > 1 ? "s" : ""
					}),
					type: "info"
				});
			});
		}
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
		<AppBar background="bg-white" padding="py-2 px-4">
			<span
				class="text-2xl font-bold pb-1 bg-gradient-to-r from-pink-500 to-violet-600 bg-clip-text text-transparent"
				id="page-title"
			>
				{safeTranslate($pageTitle)}
			</span>
			<hr class="w-screen my-1" />
			<Breadcrumbs />
		</AppBar>
	</svelte:fragment>
	<!-- Router Slot -->
	<slot />
	<!-- ---- / ---- -->
</AppShell>
