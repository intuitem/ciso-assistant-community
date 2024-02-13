<script lang="ts">
	// Most of your app wide CSS should be put in this file
	import '../../app.postcss';
	import { AppShell, AppBar } from '@skeletonlabs/skeleton';

	import SideBar from '$lib/components/SideBar/SideBar.svelte';
	import Breadcrumbs from '$lib/components/Breadcrumbs/Breadcrumbs.svelte';
	import { pageTitle } from '$lib/utils/stores';

	import * as m from '$paraglide/messages';

	let sidebarOpen = true;

	const items: any = {
		analytics: m.analytics(),
		calendar: m.calendar(),
		threats: m.threats(),
		securityFunctions: m.securityFunctions(),
		securityMeasures: m.securityMeasures(),
		assets: m.assets(),
		policies: m.policies(),
		riskMatrices: m.riskMatrices(),
		riskAssessments: m.riskAssessments(),
		riskScenarios: m.riskScenarios(),
		riskAcceptances: m.riskAcceptances(),
		complianceAssessments: m.complianceAssessments(),
		evidences: m.evidences(),
		frameworks: m.frameworks(),
		domains: m.domains(),
		projects: m.projects(),
		users: m.users(),
		userGroups: m.userGroups(),
		roleAssignments: m.roleAssignments(),
		xRays: m.xRays(),
		scoringAssistant: m.scoringAssistant(),
		libraries: m.libraries(),
		backupRestore: m.backupRestore()
	}

	$: classesSidebarOpen = (open: boolean) => (open ? 'ml-64' : 'ml-7');
</script>

<!-- App Shell -->
<AppShell
	slotPageContent="p-8 bg-slate-200"
	regionPage="transition-all duration-300 {classesSidebarOpen(sidebarOpen)}"
>
	<svelte:fragment slot="sidebarLeft">
		<SideBar bind:open={sidebarOpen} />
	</svelte:fragment>
	<svelte:fragment slot="pageHeader">
		<AppBar background="bg-white" padding="py-2 px-4">
			<span class="text-2xl font-bold pb-1" id="page-title">
				{#if items[$pageTitle]}
					{items[$pageTitle]}
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
