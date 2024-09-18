<script lang="ts">
	// Most of your app wide CSS should be put in this file
	import '../app.postcss';
	import '@fortawesome/fontawesome-free/css/all.min.css';
	import ParaglideSvelte from './ParaglideJsProvider.svelte';

	import { computePosition, autoUpdate, offset, shift, flip, arrow } from '@floating-ui/dom';

	import { getToastStore, storePopup } from '@skeletonlabs/skeleton';
	storePopup.set({ computePosition, autoUpdate, offset, shift, flip, arrow });

	// Initializing stores prevents known security issues with SvelteKit SSR
	// https://github.com/skeletonlabs/skeleton/wiki/SvelteKit-SSR-Warning
	import { initializeStores } from '@skeletonlabs/skeleton';

	initializeStores();

	import Toast from '$lib/components/Toast/Toast.svelte';
	import Modal from '$lib/components/Modals/Modal.svelte';
	import type { ModalComponent, ToastSettings } from '@skeletonlabs/skeleton';

	import { getFlash } from 'sveltekit-flash-message';
	import { page } from '$app/stores';

	const flash = getFlash(page);
	const toastStore = getToastStore();

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
					? 'variant-filled-success'
					: $flash.type === 'error'
						? 'variant-filled-error'
						: $flash.type == 'warning'
							? 'variant-filled-warning'
							: 'variant-filled-primary'
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

	let favicon: Attachment | string = '';

	import { persisted } from 'svelte-persisted-store';

	const faviconB64 = persisted('favicon', {
		data: '',
		hash: '',
		mimeType: ''
	});

	async function digestMessage(message) {
		const encoder = new TextEncoder();
		const data = encoder.encode(message);
		const hash = await window.crypto.subtle.digest('SHA-256', data);
		return hash;
	}
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
			? `data:${$faviconB64.mimeType}charset=utf-8;base64, ${$faviconB64.data}`
			: favicon;
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon && Object.hasOwn(favicon, 'url') ? favicon.url : favicon} />
</svelte:head>

<ParaglideJsProvider>
	<Modal components={modalRegistry} />
	<Toast />
	<slot />

	{#if $flash}
		{@const bg = $flash.type == 'success' ? '#3D9970' : '#FF4136'}
		<div style:background-color={bg} class="flash">{$flash.message}</div>
	{/if}
</ParaglideJsProvider>
