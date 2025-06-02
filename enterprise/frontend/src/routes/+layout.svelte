<script lang="ts">
	import { run } from 'svelte/legacy';

	// Most of your app wide CSS should be put in this file
	import '../app.css';
	import '@fortawesome/fontawesome-free/css/all.min.css';
	import ParaglideSvelte from './ParaglideJsProvider.svelte';
	import { browser } from '$app/environment';

	import { computePosition, autoUpdate, offset, shift, flip, arrow } from '@floating-ui/dom';
	storePopup.set({ computePosition, autoUpdate, offset, shift, flip, arrow });

	// Initializing stores prevents known security issues with SvelteKit SSR
	// https://github.com/skeletonlabs/skeleton/wiki/SvelteKit-SSR-Warning
	initializeStores();

	import Toast from '$lib/components/Toast/Toast.svelte';
	import Modal from '$lib/components/Modals/Modal.svelte';
	import type { ModalComponent, ToastSettings } from '@skeletonlabs/skeleton-svelte';

	import { getFlash } from 'sveltekit-flash-message';
	import { page } from '$app/stores';

	const flash = getFlash(page);
	const toastStore = getToastStore();

	import CommandPalette from '$lib/components/CommandPalette/CommandPalette.svelte';
	import commandPaletteOpen from '$lib/components/CommandPalette/CommandPalette.svelte';

	const toast = (message: string, options: Record<string, string>) => {
		const t: ToastSettings = {
			message: message,
			...options
		};
		toastStore.trigger(t);
	};

	flash.subscribe(($flash) => {
		if (!$flash) return;

		toast($flash.message, {
			background:
				$flash.type == 'success'
					? 'preset-filled-success-500'
					: $flash.type === 'error'
						? 'preset-filled-error-500'
						: $flash.type == 'warning'
							? 'preset-filled-warning-500'
							: 'preset-filled-primary-500'
		});

		// Clearing the flash message could sometimes
		// be required here to avoid double-toasting.
		flash.set(undefined);
	});

	import DisplayJSONModal from '$lib/components/Modals/DisplayJSONModal.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import DeleteConfirmModal from '$lib/components/Modals/DeleteConfirmModal.svelte';
	import ParaglideJsProvider from './ParaglideJsProvider.svelte';

	const modalRegistry: Record<string, ModalComponent> = {
		// Set a unique modal ID, then pass the component reference
		displayJSONModal: { ref: DisplayJSONModal },
		createModal: { ref: CreateModal },
		deleteConfirmModal: { ref: DeleteConfirmModal }
	};

	import { onMount } from 'svelte';

	interface Attachment {
		type: string;
		url: string;
	}

	let favicon: Attachment | string = $state('');

	import { persisted } from 'svelte-persisted-store';
	interface Props {
		children?: import('svelte').Snippet;
	}

	let { children }: Props = $props();

	const faviconB64 = persisted('favicon', {
		data: '',
		hash: '',
		mimeType: ''
	});

	const clientSettings = $page.data.clientSettings;

	onMount(async () => {
		if (!clientSettings.settings.favicon) {
			return;
		}
		const faviconHash = clientSettings.settings.favicon_hash;
		if (faviconHash !== $faviconB64.hash) {
			console.log('favicon changed, fetching new favicon...');
			const newfavicon = await fetch(`/settings/client-settings/favicon`).then((res) => res.json());
			faviconB64.set({ data: newfavicon.data, hash: faviconHash, mimeType: newfavicon.mime_type });
		}
		favicon = clientSettings.settings.favicon
			? `data:${$faviconB64.mimeType};base64, ${$faviconB64.data}`
			: favicon;
	});

	run(() => {
		if (browser && $page.url.searchParams.has('refresh')) {
			$page.url.searchParams.delete('refresh');
			window.location.href = $page.url.href;
		}
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon && Object.hasOwn(favicon, 'url') ? favicon.url : favicon} />
</svelte:head>

<ParaglideJsProvider>
	<Modal components={modalRegistry} />
	<Toast />
	<CommandPalette />
	{@render children?.()}

	{#if $flash}
		{@const bg = $flash.type == 'success' ? '#3D9970' : '#FF4136'}
		<div style:background-color={bg} class="flash">{$flash.message}</div>
	{/if}
</ParaglideJsProvider>
