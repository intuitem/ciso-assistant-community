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
			? `data:${$logoB64.mimeType};base64, ${$logoB64.data}`
			: ciso;
	});
</script>

<div class="flex flex-col items-center">
	{#if logo}
		<img {width} {height} src={logo} alt="Ciso-assistant icon" />
	{/if}
	{#if clientSettings.settings.name}
		<p class="font-semibold text-center">{clientSettings.settings.name}</p>
	{/if}
</div>
