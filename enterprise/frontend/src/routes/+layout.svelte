<script lang="ts">
	import { run } from 'svelte/legacy';

	// Most of the app wide CSS should be put in this file
	import '../app.css';
	import '@fortawesome/fontawesome-free/css/all.min.css';

	import { browser } from '$app/environment';
	import { onMount } from 'svelte';

	import Toast from '$lib/components/Toast/Toast.svelte';
	import Modal from '$lib/components/Modals/Modal.svelte';
	import DisplayJSONModal from '$lib/components/Modals/DisplayJSONModal.svelte';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import DeleteConfirmModal from '$lib/components/Modals/DeleteConfirmModal.svelte';
	import { initializeModalStore, type ModalComponent } from '$lib/components/Modals/stores';
	import {
		initializeToastStore,
		getToastStore,
		type ToastSettings
	} from '$lib/components/Toast/stores';

	import { getFlash } from 'sveltekit-flash-message';
	import { page } from '$app/stores';
	import { clientSideToast } from '$lib/utils/stores';

	initializeModalStore();
	initializeToastStore();

	const flash = getFlash(page);
	const toastStore = getToastStore();

	const toast = (message: string, options: Record<string, string>) => {
		const t: ToastSettings = {
			message: message,
			...options
		};
		toastStore.trigger(t);
	};

	interface FlashMessage {
		message: string;
		type: 'success' | 'error' | 'warning' | 'info';
	}

	function handleToast(flash: FlashMessage | undefined) {
		if (!flash) return;

		toast(flash.message, {
			background:
				flash.type == 'success'
					? 'preset-filled-success-500'
					: flash.type === 'error'
						? 'preset-filled-error-500'
						: flash.type == 'warning'
							? 'preset-filled-warning-500'
							: 'preset-filled-primary-500'
		});
	}

	clientSideToast.subscribe((flash) => {
		handleToast(flash);
		clientSideToast.set(undefined);
	});

	flash.subscribe(($flash) => {
		handleToast($flash);
		// Clearing the flash message could sometimes
		// be required here to avoid double-toasting.
		flash.set(undefined);
	});

	const modalRegistry: Record<string, ModalComponent> = {
		// Set a unique modal ID, then pass the component reference
		displayJSONModal: { ref: DisplayJSONModal },
		createModal: { ref: CreateModal },
		deleteConfirmModal: { ref: DeleteConfirmModal }
	};

	import { persisted } from 'svelte-persisted-store';
	interface Props {
		children?: import('svelte').Snippet;
	}

	let { children }: Props = $props();

	// const faviconB64 = persisted('favicon', {
	// 	data: '',
	// 	hash: '',
	// 	mimeType: ''
	// });

	const clientSettings = $page.data.clientSettings;
	// let favicon = $state($faviconB64?.hash ? `data:${$faviconB64?.mimeType};base64, ${$faviconB64?.data}` : undefined);
	// let faviconHash = $derived(clientSettings?.settings?.favicon_hash);
	//
	//  if (typeof window !== 'undefined') {
	// 	// stash the value...
	// 	const _favicon = favicon;
	//
	// 	// unset it...
	// 	favicon = undefined;
	//
	// 	$effect(() => {
	// 		// ...and reset after we've mounted
	//      // IMPORTANT: if show_images_unauthenticated is true, we show the favicon
	//      if (clientSettings?.settings?.show_images_unauthenticated || $page.data?.user) {
	//          favicon = _favicon;
	//          return;
	//      }
	//      favicon = '/favicon.ico';
	// 	});
	// }
	//
	// onMount(async () => {
	// 	if (!clientSettings?.settings?.favicon) {
	// 		return;
	// 	}
	// 	if (faviconHash !== $faviconB64?.hash) {
	// 		console.log('favicon changed, fetching new favicon...');
	// 		const newfavicon = await fetch(`/settings/client-settings/favicon`).then((res) => res.json());
	// 		faviconB64.set({ data: newfavicon.data, hash: faviconHash, mimeType: newfavicon.mime_type });
	// 	}
	// });
</script>

<svelte:head>
	<link
		rel="icon"
		type={clientSettings?.settings?.favicon_mime_type ?? 'image/x-icon'}
		href="/favicon"
	/>
</svelte:head>

<Modal components={modalRegistry} />
<Toast />
{@render children?.()}

{#if $flash}
	{@const bg = $flash.type == 'success' ? '#3D9970' : '#FF4136'}
	<div style:background-color={bg} class="flash">{$flash.message}</div>
{/if}
