<script lang="ts">
	import { m } from '$paraglide/messages';
	export let rowCount;
</script>

{#if $rowCount === undefined}
	<div />
{:else}
	<aside class="text-sm" data-testid="row-count">
		{#if $rowCount?.total > 0}
			{m.rowCount({ start: $rowCount.start, end: $rowCount.end, total: $rowCount.total })}
		{:else}
			{m.noEntriesFound()}
		{/if}
	</aside>
{/if}
