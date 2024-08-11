<script lang="ts">
	// Most of your app wide CSS should be put in this file
	import '../../app.postcss';
	import { AppShell, AppBar } from '@skeletonlabs/skeleton';

	import SideBar from '$lib/components/SideBar/SideBar.svelte';
	import Breadcrumbs from '$lib/components/Breadcrumbs/Breadcrumbs.svelte';
	import { pageTitle } from '$lib/utils/stores';

	import * as m from '$paraglide/messages.js';

	let sidebarOpen = true;

	$: classesSidebarOpen = (open: boolean) => (open ? 'ml-64' : 'ml-7');
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
				{#if Object.hasOwn(m, $pageTitle)}
					{m[$pageTitle]()}
				{:else}
					{$pageTitle}
				{/if}
			</span>
			<hr class="w-screen my-1" />
			<Breadcrumbs />
		</AppBar>
	</svelte:fragment>
	<!-- Router Slot -->
	<slot />
	<!-- ---- / ---- -->
</AppShell>
