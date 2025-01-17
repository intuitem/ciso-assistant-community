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
				title: 'Welcome!',
				description: "Let's take a tour of the main features to get you started."
			}
		},
		{
			id: 2,
			element: '#sidebar-more-btn',
			popover: {
				description: 'You can always restart this tour by clicking the help button here.'
			}
		},
		{
			id: 3,
			element: '#organization',
			popover: {
				title: 'Organization',
				description:
					'This is where you will define the hierarchy and perimeters of your organization. Click here.'
			}
		},
		{
			id: 4,
			element: '#domains',
			popover: {
				description:
					'Domains allow you to isolate your objects using the associated roles. You will need at least one. Click here.'
			}
		},
		{
			id: 5,
			element: '#add-button',
			popover: {
				description: 'This where you will be able to create a new domain.'
			}
		},
		{
			id: 6,
			element: '#projects',
			popover: {
				description:
					'Projects are functional perimeters within a domain. You will need at least one. Click here.'
			}
		},
		{
			id: 7,
			element: '#add-button',
			popover: {
				description: 'This is where you will be able to create a project.'
			}
		},
		{
			id: 8,
			element: '#catalog-step',
			popover: {
				title: 'Catalog Overview',
				description:
					'The catalog is where you will be able to import frameworks, threats, matrices and other predifined objects'
			}
		},
		{
			id: 9,
			element: '#catalog',
			popover: {
				description:
					'You will be able to browse the loaded objects per category and import new ones'
			}
		},
		{
			id: 10,
			element: '#frameworks',
			popover: {
				title: 'Frameworks',
				description:
					'View and manage compliance frameworks. You will need at least one to initiate an audit. Click here.'
			}
		},
		{
			id: 11,
			element: '#add-button',
			popover: {
				description: 'Import new frameworks here.'
			}
		},
		{
			id: 14,
			element: '#riskMatrices',
			popover: {
				title: 'Risk Matrices',
				description:
					'View and manage risk matrices. You will need at least one to initiate a risk assessment. Click here.'
			}
		},
		{
			id: 11,
			element: '#add-button',
			popover: {
				description: 'Import new matrices here.'
			}
		},
		{
			id: 17,
			element: '#compliance',
			popover: {
				description: 'This where will be able to manage your compliance activities. Click here.'
			}
		},
		{
			id: 18,
			element: '#complianceAssessments',
			popover: {
				title: 'Audits',
				description: 'This is where you will be able to drive and track your audits and baselines'
			}
		},
		{
			id: 19,
			element: '#risk',
			popover: {
				description:
					'This is where you will be able to manage your risk analysis and registry. Click here.'
			}
		},
		{
			id: 20,
			element: '#riskAssessments',
			popover: {
				title: 'Risk Assessment',
				description: 'Group and manage your analysis through risk assessments.'
			}
		},
		{
			id: 20,
			element: '#overview',
			popover: {
				title: 'Analytics',
				description: 'The overview section cover your main dashboards and analytics.'
			}
		},
		{
			id: 21,
			element: '#analytics',
			popover: {
				description: 'View the aggregated analytics and reports here.'
			}
		},
		{
			id: 22,
			element: '#myAssignments',
			popover: {
				description: 'or track your indivdual assignements and tasks here.'
			}
		},
		{
			id: 23,
			element: '#sidebar-more-btn',
			popover: {
				title: 'Help & Tour',
				description: 'Remember, you can always restart the tour from here!'
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
