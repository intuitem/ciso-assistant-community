<script lang="ts">
	import { BASE_API_URL } from '$lib/utils/constants';
	import ciso from '$lib/assets/ciso.svg';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';

	export let height = 200;
	export let width = 200;

	const clientSettings = $page.data.clientSettings;
	let logo: string;

	onMount(async () => {
		logo = clientSettings.settings.logo
			? `${BASE_API_URL}/client-settings/${clientSettings.settings.id}/logo/`
			: ciso;
	});
</script>

{#if logo}
	<img width={200} height={200} src={logo} alt="Ciso-assistant icon" />
{/if}
