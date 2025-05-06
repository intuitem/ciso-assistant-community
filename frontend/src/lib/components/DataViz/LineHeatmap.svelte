<script lang="ts">
	export let data;
	import { safeTranslate } from '$lib/utils/i18n';
</script>

<div class="flex w-full border">
	{#each data as entry}
		<div class="p-2 flex-grow" style="background-color: {entry.impact.hexcolor};">
			<div class="text-lg font-bold">{safeTranslate(entry.impact.name)}</div>
			<div>{entry.pit}</div>
		</div>
	{/each}
</div>
