<script lang="ts" type="module">
	import { onMount } from 'svelte';
	import SideBarFooter from './SideBarFooter.svelte';
	import SideBarHeader from './SideBarHeader.svelte';
	import SideBarNavigation from './SideBarNavigation.svelte';
	import SideBarToggle from './SideBarToggle.svelte';
	import { writable } from 'svelte/store';

	import { getCookie, setCookie } from '$lib/utils/cookies';
	import { driverInstance } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';

	import { invalidateAll } from '$app/navigation';
	import { page } from '$app/stores';
	import FirstLoginModal from '$lib/components/Modals/FirstLoginModal.svelte';
	import { breadcrumbs, goto } from '$lib/utils/breadcrumbs';
	import { getModalStore, type ModalComponent, type ModalSettings } from '@skeletonlabs/skeleton';
	import { driver } from 'driver.js';
	import 'driver.js/dist/driver.css';
	import { getFlash } from 'sveltekit-flash-message';
	import './driver-custom.css';
	import LoadingSpinner from '../utils/LoadingSpinner.svelte';

	export let open: boolean;

	const user = $page.data?.user;

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
			element: '#perimeters',
			popover: {
				description: m.tourPerimetersDescription()
			}
		},
		{
			id: 7,
			element: '#add-button',
			popover: {
				description: m.tourPerimeterAddDescription()
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

	const modalStore = getModalStore();
	const flash = getFlash(page);

	function modalFirstLogin(): void {
		const modalComponent: ModalComponent = {
			ref: FirstLoginModal,
			props: {
				actions: [
					{
						label: m.showGuidedTour(),
						action: triggerVisit,
						classes: 'variant-filled-surface',
						btnIcon: 'fa-wand-magic-sparkles'
					},
					{
						label: m.loadDemoData(),
						action: loadDemoDomain,
						classes: 'variant-filled-secondary',
						btnIcon: 'fa-file-import',
						async: true
					}
				]
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: m.firstTimeLoginModalTitle(),
			body: m.firstTimeLoginModalDescription()
		};
		modalStore.trigger(modal);
	}

	const loading = writable(false);

	async function loadDemoDomain() {
		$loading = true;
		const response = await fetch('/folders/import-dummy/', { method: 'POST' });
		if (!response.ok) {
			if (response.status === 500) {
				flash.set({ type: 'error', message: m.demoDataAlreadyImported() });
			} else {
				flash.set({ type: 'error', message: m.errorOccuredDuringImport() });
			}
			console.error('Failed to load demo data');
			$loading = false;
			return false;
		}
		flash.set({ type: 'success', message: m.successfullyImportedFolder() });

		await goto('/folders', {
			crumbs: breadcrumbs,
			label: m.domains(),
			breadcrumbAction: 'replace'
		});

		invalidateAll();
		$loading = false;
		return true;
	}

	function triggerVisit() {
		const translatedSteps = steps;
		const driverObj = driver({
			showProgress: true,
			steps: translatedSteps,
			popoverClass: 'custom-driver-theme'
		});
		$driverInstance = driverObj;
		driverObj.drive();
		return true;
	}

	onMount(() => {
		const showFirstLoginModal =
			getCookie('show_first_login_modal') === 'true' && user.accessible_domains.length === 0;
		// NOTE: For now, there is only a single guided tour, which is targeted at an administrator.
		// Later, we will have tours for domain managers, analysts etc.
		if (showFirstLoginModal && user.is_admin) {
			modalFirstLogin();
		}
		setCookie('show_first_login_modal', 'false');
	});

	$: classesSidebarOpen = (open: boolean) => (open ? '' : '-ml-[14rem] pointer-events-none');
</script>

<div data-testid="sidebar">
	<aside
		class="flex w-64 shadow transition-all duration-300 fixed h-screen overflow-visible top-0 left-0 z-20 {classesSidebarOpen(
			open
		)}"
	>
		<nav class="flex-1 flex flex-col overflow-y-auto overflow-x-hidden bg-gray-50 py-4 px-3">
			<SideBarHeader />
			<SideBarNavigation />
			<SideBarFooter on:triggerGT={triggerVisit} on:loadDemoDomain={loadDemoDomain} />
		</nav>
	</aside>
	{#if $loading}
		<div class="fixed inset-0 flex items-center justify-center bg-gray-50 bg-opacity-50 z-[1000]">
			<div class="flex flex-col items-center space-y-2">
				<LoadingSpinner></LoadingSpinner>
			</div>
		</div>
	{/if}
	<SideBarToggle bind:open />
</div>
