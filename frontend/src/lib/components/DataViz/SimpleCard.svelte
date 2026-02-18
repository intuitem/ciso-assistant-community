<script lang="ts">
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	interface Props {
		count?: string;
		label: string;
		href?: string;
		emphasis?: boolean;
		customClass?: string;
	}

	let { count = '0', label, href = '#', emphasis = false, customClass = '' }: Props = $props();

	// Enhanced emphasis styling
	const emphasisClasses = emphasis
		? 'border-l-4 border-l-violet-500 bg-gradient-to-r from-violet-25 to-surface-50-950 shadow-md'
		: 'border border-surface-200-800';

	// Base card styling - clean and minimal
	const baseCardClasses = `
		flex flex-col h-20 p-3 bg-surface-50-950 rounded-lg
		transition-all duration-200 ease-in-out
		group cursor-pointer
		hover:shadow-lg hover:shadow-violet-100 hover:-translate-y-0.5
		${emphasisClasses} ${customClass}
	`;

	// Format count with proper formatting for numbers, percentages, and ratios
	const formattedCount = $derived(() => {
		// Convert to string first to handle both string and number inputs
		const countStr = String(count);

		// If it already contains % or /, return as-is since it's already formatted
		if (countStr.includes('%') || countStr.includes('/')) {
			return countStr;
		}

		// Try to parse as number for thousand separators
		const numericCount = parseInt(countStr);
		return isNaN(numericCount) ? countStr : numericCount.toLocaleString();
	});
</script>

{#snippet cardContent()}
	<div class="flex-1 flex flex-col justify-center">
		<div
			class="text-2xl font-bold text-surface-950-50 leading-none mb-1 group-hover:text-violet-800 transition-colors duration-200"
		>
			{formattedCount()}
		</div>
		<div
			class="text-xs font-medium text-surface-600-400 capitalize group-hover:text-violet-700 transition-colors duration-200"
		>
			{label}
		</div>
	</div>
{/snippet}

{#if href && href !== '#'}
	<Anchor {href} {label} class="{baseCardClasses} text-surface-950-50">
		{@render cardContent()}
	</Anchor>
{:else}
	<div class="{baseCardClasses} text-surface-950-50">
		{@render cardContent()}
	</div>
{/if}
