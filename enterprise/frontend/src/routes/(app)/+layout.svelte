<script lang="ts">
	import { run } from 'svelte/legacy';

	import CommandPalette from '$lib/components/CommandPalette/CommandPalette.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { AppBar } from '@skeletonlabs/skeleton-svelte';
	import '../../app.css';

	import { browser } from '$app/environment';
	import Breadcrumbs from '$lib/components/Breadcrumbs/Breadcrumbs.svelte';
	import SideBar from '$lib/components/SideBar/SideBar.svelte';
	import { deleteCookie, getCookie } from '$lib/utils/cookies';
	import { clientSideToast, pageTitle, modelName, modelDescription } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import { page } from '$app/stores';
	import type { LayoutData } from './$types';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';

	interface Props {
		data: LayoutData;
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

	let sidebarOpen = $state(true);

	let classesSidebarOpen = $derived((open: boolean) => (open ? 'ml-64' : 'ml-7'));

	// Display title, model name, and description from either page data or manual store setting
	const displayTitle = $derived($page.data?.title || $pageTitle);

	// Auto-detect model from URL for list pages
	// Match pattern: /model-name or /model-name/ (but not /model-name/uuid or /model-name/something)
	const urlModel = $derived(() => {
		const path = $page.url.pathname;
		const match = path.match(/^\/([a-z-]+)\/?$/);
		return match ? match[1] : null;
	});

	// Generate description key from URL model: "risk-matrices" → "riskMatricesDescription"
	const urlDescriptionKey = $derived(() => {
		const model = urlModel();
		if (!model) return null;

		const camelCase = model
			.split('-')
			.map((word, index) => (index === 0 ? word : word.charAt(0).toUpperCase() + word.slice(1)))
			.join('');
		return `${camelCase}Description`;
	});

	// Determine if we're on a list page vs detail page
	// List page: URL matches /model-name pattern (e.g., /risk-assessments)
	// Detail page: has an object title from loadDetail (e.g., /risk-assessments/uuid)
	const matchesListUrl = $derived(!!urlModel());
	const hasObjectTitle = $derived(!!$page.data?.title);

	// For list pages: show description subtitle
	// For detail pages: show model name subtitle
	const displayModelName = $derived(
		hasObjectTitle ? $page.data?.modelVerboseName || $modelName : ''
	);

	const displayModelDescription = $derived(
		(() => {
			// Only show description on list pages (not on detail pages with object titles)
			if (hasObjectTitle) return '';
			if (!matchesListUrl && !$page.data?.modelDescriptionKey) return '';

			// List pages: get description from i18n
			const descKey = $page.data?.modelDescriptionKey || urlDescriptionKey();
			if (descKey && m[descKey]) {
				return m[descKey]();
			}

			// Fallback to manual store
			return $modelDescription;
		})()
	);

	run(() => {
		if (browser) {
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
	});

	const licenseExpirationNotifyDays = data.LICENSE_EXPIRATION_NOTIFY_DAYS;
	const licenseStatus: Record<string, any> = data.licenseStatus;

	const licenseAboutToExpire =
		licenseStatus?.status === 'active' && licenseStatus?.days_left <= licenseExpirationNotifyDays;
	import type { PageData, ActionData } from './$types';
	import QuickStartModal from '$lib/components/SideBar/QuickStart/QuickStartModal.svelte';

	import { getSidebarVisibleItems } from '$lib/utils/sidebar-config';
	import { interceptExternalLinks, setGlobalModalStore } from '$lib/utils/external-links';

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

	// Initialize external link interceptor
	$effect(() => {
		if (browser) {
			setGlobalModalStore(modalStore);
			interceptExternalLinks();
		}
	});
</script>

<!-- App Shell -->
<div class="overflow-x-hidden">
	<SideBar bind:open={sidebarOpen} {sideBarVisibleItems} />
	{#if data.licenseStatus.status === 'expired'}
		<aside class="preset-tonal-warning text-center w-full items-center py-2">
			{m.licenseExpiredMessage()}
		</aside>
	{:else if licenseAboutToExpire}
		<aside class="preset-tonal-warning text-center w-full items-center py-2">
			{m.licenseAboutToExpireWarning({ days_left: licenseStatus.days_left })}
		</aside>
	{/if}
	<AppBar
		base="relative transition-all duration-300 {classesSidebarOpen(sidebarOpen)}"
		background="bg-white"
		padding="pb-2 px-4"
	>
		{#snippet headline()}
			<div
				class="text-2xl font-bold pb-1 bg-linear-to-r from-pink-500 to-violet-600 bg-clip-text text-transparent"
				id="page-title"
			>
				{safeTranslate(displayTitle)}
			</div>
			{#if displayModelName}
				<div class="text-sm text-slate-500 font-medium">
					{safeTranslate(displayModelName)}
				</div>
			{/if}
			{#if displayModelDescription}
				<div class="text-xs text-slate-400 italic">
					{safeTranslate(displayModelDescription)}
				</div>
			{/if}
			{#if data?.user?.is_admin}
				<button
					onclick={modalQuickStart}
					class="absolute top-7 right-9 p-2 rounded-full bg-violet-500 text-white text-xs shadow-lg
        ring-2 ring-violet-400 ring-offset-2 transition-all duration-300 hover:bg-violet-600
        hover:ring-violet-300 hover:ring-offset-violet-100 hover:shadow-violet-500/50
        focus:outline-hidden focus:ring-violet-500"
				>
					{m.quickStart()}
				</button>
			{/if}
			<hr class="w-screen my-1" />
			<Breadcrumbs />
		{/snippet}
	</AppBar>
	<!-- Router Slot -->
	<CommandPalette />
	<main
		class="min-h-screen p-8 bg-linear-to-br from-violet-100 to-slate-200 transition-all duration-300 {classesSidebarOpen(
			sidebarOpen
		)}"
	>
		{@render children?.()}
	</main>
	<!-- ---- / ---- -->
</div>
