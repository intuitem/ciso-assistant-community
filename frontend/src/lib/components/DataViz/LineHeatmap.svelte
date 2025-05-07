<script lang="ts">
	export let data;
	import { safeTranslate } from '$lib/utils/i18n';
</script>

<div class="flex w-full border">
	{#if !data || data.length === 0}
		<div class="p-4 text-center w-full text-gray-500">
			{safeTranslate('noDataAvailable')}
		</div>
	{:else}
		{#each data as entry}
			<div class="p-2 flex-grow" style="background-color: {entry?.impact?.hexcolor || '#f0f0f0'};">
				<div class="text-lg font-bold">{safeTranslate(entry?.impact?.name || 'unknown')}</div>
				<div>{entry?.pit || '-'}</div>
			</div>
		{/each}
	{/if}
</div>
