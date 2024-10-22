<script lang="ts">
	import type { PageData } from './$types';
	import Logo from '$lib/components/Logo/Logo.svelte';
	import Greetings from './Greetings.svelte';
	import FormCard from './FormCard.svelte';

	export let data: PageData;
</script>

<div class="relative h-screen w-screen bg-slate-200">
	<div class="absolute top-5 left-5">
		<div class="flex flex-row max-w-48 space-x-4 pb-3">
			{#if !data.clientSettings.settings.name}
				<Logo />
			{/if}
		</div>
	</div>
	<div class="absolute top-1/2 left-1/2 w-full transform -translate-x-1/2 -translate-y-1/2">
		<div class="flex flex-row w-full pr-8">
			<Greetings />
			<div class="flex justify-center pr-5 items-center space-y-4 w-2/5">
				<FormCard {data} />
			</div>
		</div>
	</div>
</div>
