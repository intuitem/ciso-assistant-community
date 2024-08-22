<script lang="ts">
	import { BASE_API_URL } from '$lib/utils/constants';
	import ciso from '$lib/assets/ciso.svg';
	import { onMount } from 'svelte';

	export let height = 200;
	export let width = 200;

	let clientSettings: Record<string, any>;
	let logo: string;

	onMount(async () => {
		clientSettings = await fetch('/settings/client-settings').then((res) => res.json());
		logo = clientSettings.logo
			? `${BASE_API_URL}/client-settings/${clientSettings.id}/logo/`
			: ciso;
	});
</script>

{#if logo}
	<img width={200} height={200} src={logo} alt="Ciso-assistant icon" />
{/if}
