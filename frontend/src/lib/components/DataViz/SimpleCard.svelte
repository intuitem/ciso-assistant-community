<script lang="ts">
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	interface Props {
		count?: string;
		label: string;
		href?: string;
		emphasis?: boolean;
		customClass?: string;
	}

	let {
		count = '0',
		label,
		href = '#',
		emphasis = false,
		customClass = ''
	}: Props = $props();

	// Enhanced emphasis styling
	const emphasisClasses = emphasis
		? 'border-l-4 border-l-violet-500 bg-gradient-to-r from-violet-25 to-white shadow-md'
		: 'border border-gray-200';

	// Base card styling - clean and minimal
	const baseCardClasses = `
		flex flex-col h-20 p-3 bg-white rounded-lg
		transition-all duration-200 ease-in-out
		group cursor-pointer
		hover:shadow-lg hover:shadow-violet-100 hover:-translate-y-0.5
		${emphasisClasses} ${customClass}
	`;

	// Format count with thousand separators if it's a number
	const formattedCount = $derived(() => {
		const numericCount = parseInt(count);
		return isNaN(numericCount) ? count : numericCount.toLocaleString();
	});
</script>

{#snippet cardContent()}
	<div class="flex-1 flex flex-col justify-center">
		<div class="text-2xl font-bold text-gray-800 leading-none mb-1 group-hover:text-violet-800 transition-colors duration-200">
			{formattedCount()}
		</div>
		<div class="text-xs font-medium text-gray-600 capitalize group-hover:text-violet-700 transition-colors duration-200">
			{label}
		</div>
	</div>
{/snippet}

{#if href && href !== '#'}
	<Anchor {href} {label} class="{baseCardClasses} text-gray-800">
		{@render cardContent()}
	</Anchor>
{:else}
	<div class="{baseCardClasses} text-gray-800">
		{@render cardContent()}
	</div>
{/if}
