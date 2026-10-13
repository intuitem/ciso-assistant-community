<script lang="ts">
	import { isDark } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		cell: { name?: string; str?: string; hexcolor?: string } | null | undefined;
		[key: string]: any;
	}

	let { cell, ...rest }: Props = $props();
	let color = $derived(cell?.hexcolor || '#94a3b8');
</script>

{#if cell}
	<span
		{...rest}
		class="inline-flex w-fit min-w-20 justify-center px-2 py-0.5 rounded-md whitespace-nowrap text-sm {isDark(
			color
		)
			? 'text-white'
			: 'text-surface-950'}"
		style="background-color: {color}"
	>
		{safeTranslate(cell.name ?? cell.str ?? '')}
	</span>
{:else}
	<span {...rest}>--</span>
{/if}
