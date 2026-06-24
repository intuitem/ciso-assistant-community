<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate, unsafeTranslate } from '$lib/utils/i18n';
	import { isDark } from '$lib/utils/helpers';
	let { data } = $props();

	// On a fixed impact hexcolor, pick black/white text by luminance; with no color, fall back
	// to the theme surface so the cell and its text stay readable in both light and dark.
	function cellBg(impact: { hexcolor?: string } | undefined) {
		return impact?.hexcolor || 'var(--color-surface-100-900)';
	}
	function cellTextClass(impact: { hexcolor?: string } | undefined) {
		if (!impact?.hexcolor) return 'text-surface-950-50';
		return isDark(impact.hexcolor) ? 'text-white' : 'text-surface-950';
	}
</script>

<div class="flex w-full border" data-testid="line-heatmap">
	{#if !data || data.length === 0}
		<div class="p-4 text-center w-full text-surface-600-400">
			{m.noDataAvailable()}
		</div>
	{:else}
		{#each data as entry}
			<div
				class="p-2 grow {cellTextClass(entry?.impact)}"
				style="background-color: {cellBg(entry?.impact)};"
			>
				<div class="text-lg font-bold">
					{safeTranslate(entry?.impact?.name || 'unknown')}
				</div>
				<div>{unsafeTranslate(entry?.pit) || '-'}</div>
			</div>
		{/each}
	{/if}
</div>
