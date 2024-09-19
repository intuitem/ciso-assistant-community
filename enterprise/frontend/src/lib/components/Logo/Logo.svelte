<script lang="ts">
	import ciso from '$lib/assets/ciso.svg';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { persisted } from 'svelte-persisted-store';

	const logoB64 = persisted('logo', {
		data: '',
		hash: '',
		mimeType: ''
	});

	export let height = 200;
	export let width = 200;

	const clientSettings = $page.data.clientSettings;
	let logo: string;

	onMount(async () => {
		if (!clientSettings.settings.logo) {
			logo = ciso;
			return;
		}
		const logoHash = clientSettings.settings.logo_hash;
		if (logoHash !== $logoB64.hash) {
			console.log('Logo changed, fetching new logo...');
			const newLogo = await fetch(`/settings/client-settings/logo`).then((res) => res.json());
			logoB64.set({ data: newLogo.data, hash: logoHash, mimeType: newLogo.mime_type });
		}
		logo = clientSettings.settings.logo
			? `data:${$logoB64.mimeType}charset=utf-8;base64, ${$logoB64.data}`
			: ciso;
	});
</script>

{#if logo}
	<img width={200} height={200} src={logo} alt="Ciso-assistant icon" />
{/if}
