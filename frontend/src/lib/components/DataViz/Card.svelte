<script lang="ts">
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	let cEmphasis = $state('');
	interface Props {
		count?: string;
		label: string;
		href?: string;
		// export let help: string;
		icon?: string;
		section?: string;
		emphasis?: boolean;
		customClass?: string;
	}

	let {
		count = '0',
		label,
		href = '#',
		icon = '',
		section = '',
		emphasis = false,
		customClass = ''
	}: Props = $props();

	if (emphasis) {
		cEmphasis = 'border border-y-0 border-r-0 border-l-2 border-l-violet-600';
	}
</script>

{#if href && href !== '#'}
	<Anchor
		{href}
		{label}
		class="flex flex-col shadow-lg text-purple-800 p-2 h-20 bg-surface-50-950 hover:bg-violet-50 {cEmphasis} {customClass}"
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
			<p class="text-2xl font-bold text-left" data-testid="card-{section}-{label}">{count}</p>
			<div class="text-xs">{label}</div>
		</div>
	</Anchor>
{:else}
	<div
		class="flex flex-col shadow-lg text-purple-800 p-2 h-20 bg-surface-50-950 {cEmphasis} {customClass}"
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
			<p class="text-2xl font-bold text-left" data-testid="card-{section}-{label}">{count}</p>
			<div class="text-xs">{label}</div>
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
