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
				title: m.gtSidebarStep01Msg(),
				description: m.gtSidebarStep01Desc()
			}
		},
		{
			id: 18,
			element: '#sidebar-more-btn',
			popover: {
				description: m.gtSidebarStep18Desc()
			}
		},
		{
			id: 2,
			element: '#organization',
			popover: {
				title: m.gtSidebarStepClickHere()
			}
		},
		{
			id: 3,
			element: '#domains',
			popover: {
				title: m.gtSidebarStepClickHere(),
				description: m.gtSidebarStep03Desc()
			}
		},
		{
			id: 4,
			element: '#add-button',
			popover: {
				description: 'You will need to create a first domain to get started'
			}
		},
		{
			id: 4,
			element: '#form-input-name',
			popover: {
				description: 'choose a name for your domain (eg. my organization, my departement)'
			}
		},
		{
			id: 5,
			element: '#catalog',
			popover: {
				title: m.gtSidebarStepClickHere(),
				description:
					'The library of CISO Assistant is quite comprehensive and contain multiple objects: frameworks, threats, matrices.'
			}
		},
		{ id: 6, element: '#frameworks', popover: { title: 'click here' } },
		{
			id: 7,
			element: '#add-button',
			popover: { title: 'Click to import one', description: 'Description' }
		},
		{
			id: 8,
			element: '#search-input',
			popover: { title: 'Type to filter', description: 'You can try csf v2' }
		},
		{
			id: 9,
			element: '#tablerow-import-button',
			popover: { title: 'Click here to load it' }
		},
		{
			id: 10,
			element: '#riskMatrices',
			popover: {
				title: m.gtSidebarStepClickHere(),
				description:
					"You will also need a matrix for your risk assessment. Let's filter the library content to focus on that."
			}
		},
		{
			id: 11,
			element: '#add-button',
			popover: { title: 'Click to import one', description: 'Description' }
		},
		{
			id: 12,
			element: '#filters',
			popover: {
				description:
					'Notice that we came back to the library view with an extra filter being applied.'
			}
		},
		{
			id: 13,
			element: '#tablerow-import-button',
			popover: { title: 'Click here to load it' }
		},
		{
			id: 14,
			element: '#compliance',
			popover: {
				title: m.gtSidebarStepClickHere()
			}
		},
		{
			id: 15,
			element: '#complianceAssessments',
			popover: {
				description:
					'This is where you can create and manage your audits that will serve as your baseline'
			}
		},
		{ id: 16, element: '#risk', popover: { title: m.gtSidebarStepClickHere() } },
		{
			id: 17,
			element: '#riskAssessments',
			popover: {
				description: 'And this is where you will be able to perform your risk assessments'
			}
		},
		{
			id: 18,
			element: '#sidebar-more-btn',
			popover: {
				description: m.gtSidebarStep18Desc()
			}
		},
		{
			id: 19,
			element: 'none',
			popover: {
				title: 'All set',
				description:
					'You are good to go. Feel free to reach out the Discord server to interact with the growing community!'
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
