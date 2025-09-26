<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	let { data } = $props();
</script>

<div class="flex w-full border" data-testid="line-heatmap">
	{#if !data || data.length === 0}
		<div class="p-4 text-center w-full text-gray-500">
			{m.noDataAvailable()}
		</div>
	{:else}
		{#each data as entry}
			<div class="p-2 grow" style="background-color: {entry?.impact?.hexcolor || '#f0f0f0'};">
				<div class="text-lg font-bold">
					{safeTranslate(entry?.impact?.name || 'unknown')}
				</div>
				<div>{safeTranslate(entry?.pit) || '-'}</div>
			</div>
		{/each}
	{/if}
</div>
