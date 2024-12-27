<script lang="ts">
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	export let count: string = '0';
	export let label: string;
	export let href: string = '#';
	// export let help: string;
	export let icon: string = '';
	export let section: string = '';
	export let emphasis: boolean = false;
	let cEmphasis = '';
	if (emphasis) {
		cEmphasis = 'border border-y-0 border-r-0 border-l-2 border-l-violet-600';
	}
	export let customClass: string = '';
</script>

{#if href && href !== '#'}
	<Anchor
		{href}
		{label}
		class="flex flex-col shadow-lg text-purple-800 p-2 h-28 bg-white hover:bg-violet-50 {cEmphasis} {customClass}"
	>
		<div class="text-xs">
			{#if icon}
				<span><i class={icon}></i></span>
			{/if}
			{#if section}
				<span>{section}</span>
			{/if}
		</div>
		<div class="mt-auto">
			<p class="text-4xl font-bold text-left">{count}</p>
			<div class="text-sm">{label}</div>
		</div>
	</Anchor>
{:else}
	<div class="flex flex-col shadow-lg text-purple-800 p-2 h-28 bg-white {cEmphasis} {customClass}">
		<div class="text-xs">
			{#if icon}
				<span><i class={icon}></i></span>
			{/if}
			{#if section}
				<span>{section}</span>
			{/if}
		</div>
		<div class="mt-auto">
			<p class="text-4xl font-bold text-left">{count}</p>
			<div class="text-sm">{label}</div>
		</div>
	</div>
{/if}

<style>
	@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap');

	.custom-font {
		font-family: 'Inter', sans-serif;
		font-optical-sizing: auto;
		font-style: normal;
	}
</style>
