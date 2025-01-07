<script lang="ts" type="module">
	import SideBarFooter from './SideBarFooter.svelte';
	import SideBarHeader from './SideBarHeader.svelte';
	import SideBarNavigation from './SideBarNavigation.svelte';
	import SideBarToggle from './SideBarToggle.svelte';
	import { onMount } from 'svelte';
	export let open: boolean;

	$: classesSidebarOpen = (open: boolean) => (open ? '' : '-ml-[14rem] pointer-events-none');

	import { driver } from 'driver.js';
	import 'driver.js/dist/driver.css';

	const driverObj = driver();
	onMount(() => {
		const driverObj = driver({
			showProgress: true,
			steps: [
				{
					element: 'none',
					popover: {
						title: 'Welcome !',
						description:
							'The quick guided tour will help setup the main parts to get started with CISO Assistant.'
					}
				},
				{
					element: '#organization',
					popover: {
						title: 'Click to unfold',
						description: 'This section will help you define the scopes of your work.'
					}
				},
				{
					element: '#domains',
					popover: {
						title: 'Click here',
						description: 'You will need to create a first domain to get started'
					}
				},
				{
					element: '#add-button',
					popover: {
						title: 'Click here',
						description: 'You will need to create a first domain to get started'
					}
				},
				{
					element: 'none',
					popover: {
						title: 'The catalog',
						description:
							'The library of CISO Assistant is quite comprehensive and contain multiple objects: frameworks, threats, matrices.'
					}
				},
				{
					element: '#catalog',
					popover: { title: 'Click to unfold' }
				},
				{ element: '#frameworks', popover: { title: 'Title', description: 'Description' } },
				{
					element: '#add-button',
					popover: { title: 'Click to import one', description: 'Description' }
				},
				{
					element: '#riskMatrices',
					popover: {
						title: 'Title',
						description: 'You need a framework and a matrix to get  started'
					}
				},
				{ element: '#compliance', popover: { title: 'Title', description: 'Description' } },
				{
					element: '#complianceAssessments',
					popover: { title: 'Title', description: 'Description' }
				},
				{ element: '#risk', popover: { title: 'Title', description: 'Description' } },
				{ element: '#riskAssessments', popover: { title: 'Title', description: 'Description' } }
			]
		});

		driverObj.drive();
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
		<SideBarFooter />
	</nav>
</aside>

<SideBarToggle bind:open />
