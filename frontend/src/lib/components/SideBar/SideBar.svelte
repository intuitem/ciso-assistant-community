<script lang="ts" type="module">
	import SideBarFooter from './SideBarFooter.svelte';
	import SideBarHeader from './SideBarHeader.svelte';
	import SideBarNavigation from './SideBarNavigation.svelte';
	import SideBarToggle from './SideBarToggle.svelte';
	import { onMount } from 'svelte';
	export let open: boolean;
	export let firstTime = false; // this needs to come from the db ; we also need to make room for variable about the specialized guided tours
	import { driverInstance } from '$lib/utils/stores';
	$: classesSidebarOpen = (open: boolean) => (open ? '' : '-ml-[14rem] pointer-events-none');

	import { safeTranslate } from '$lib/utils/i18n';
	import * as m from '$paraglide/messages';

	// id is not needed, just to help us with authoring
	// this is not great, but couldn't find a way for i18n while separating the file.
	const steps = [
		{
			id: 1,
			element: 'none',
			popover: {
				title: m.tourWelcomeTitle(),
				description: m.tourWelcomeDescription()
			}
		},
		{
			id: 2,
			element: '#sidebar-more-btn',
			popover: {
				description: m.tourHelpButtonDescription()
			}
		},
		{
			id: 3,
			element: '#organization',
			popover: {
				title: m.tourOrganizationTitle(),
				description: m.tourOrganizationDescription()
			}
		},
		{
			id: 4,
			element: '#domains',
			popover: {
				description: m.tourDomainsDescription()
			}
		},
		{
			id: 5,
			element: '#add-button',
			popover: {
				description: m.tourDomainAddDescription()
			}
		},
		{
			id: 6,
			element: '#projects',
			popover: {
				description: m.tourProjectsDescription()
			}
		},
		{
			id: 7,
			element: '#add-button',
			popover: {
				description: m.tourProjectAddDescription()
			}
		},
		{
			id: 8,
			element: '#catalog-step',
			popover: {
				title: m.tourCatalogTitle(),
				description: m.tourCatalogDescription()
			}
		},
		{
			id: 9,
			element: '#catalog',
			popover: {
				description: m.tourCatalogBrowseDescription()
			}
		},
		{
			id: 10,
			element: '#frameworks',
			popover: {
				title: m.tourFrameworksTitle(),
				description: m.tourFrameworksDescription()
			}
		},
		{
			id: 11,
			element: '#add-button',
			popover: {
				description: m.tourFrameworkAddDescription()
			}
		},
		{
			id: 12,
			element: '#riskMatrices',
			popover: {
				title: m.tourRiskMatricesTitle(),
				description: m.tourRiskMatricesDescription()
			}
		},
		{
			id: 13,
			element: '#add-button',
			popover: {
				description: m.tourMatricesAddDescription()
			}
		},
		{
			id: 14,
			element: '#compliance',
			popover: {
				description: m.tourComplianceDescription()
			}
		},
		{
			id: 15,
			element: '#complianceAssessments',
			popover: {
				title: m.tourAuditsTitle(),
				description: m.tourAuditsDescription()
			}
		},
		{
			id: 16,
			element: '#risk',
			popover: {
				description: m.tourRiskDescription()
			}
		},
		{
			id: 17,
			element: '#riskAssessments',
			popover: {
				title: m.tourRiskAssessmentTitle(),
				description: m.tourRiskAssessmentDescription()
			}
		},
		{
			id: 18,
			element: '#overview',
			popover: {
				title: m.tourAnalyticsTitle(),
				description: m.tourAnalyticsDescription()
			}
		},
		{
			id: 19,
			element: '#analytics',
			popover: {
				description: m.tourAnalyticsViewDescription()
			}
		},
		{
			id: 20,
			element: '#myAssignments',
			popover: {
				description: m.tourAssignmentsDescription()
			}
		},
		{
			id: 21,
			element: '#sidebar-more-btn',
			popover: {
				title: m.tourHelpFinalTitle(),
				description: m.tourHelpFinalDescription()
			}
		}
	];

	function wrapStepWithTranslation(step: any) {
		const { popover, ...rest } = step;

		if (!popover) return step;

		return {
			...rest,
			popover: {
				...popover,
				title: safeTranslate(popover.title),
				description: safeTranslate(popover.description)
			}
		};
	}
	import { driver } from 'driver.js';
	import 'driver.js/dist/driver.css';
	import { description } from '$paraglide/messages/ro';

	function triggerVisit() {
		const translatedSteps = steps; //steps.map(wrapStepWithTranslation);
		const driverObj = driver({
			showProgress: true,
			steps: translatedSteps
		});
		$driverInstance = driverObj;
		driverObj.drive();
	}
	onMount(() => {
		if (firstTime) {
			triggerVisit();
		}
	});
</script>

<aside
	class="flex w-64 shadow transition-all duration-300 fixed h-screen overflow-visible top-0 left-0 z-20 {classesSidebarOpen(
		open
	)}"
>
	<nav class="flex-1 flex flex-col overflow-y-auto overflow-x-hidden bg-gray-50 py-4 px-3">
		<SideBarHeader />
		<SideBarNavigation />
		<SideBarFooter on:triggerGT={triggerVisit} />
	</nav>
</aside>

<SideBarToggle bind:open />
