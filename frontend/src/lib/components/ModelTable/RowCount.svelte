<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { m } from '$paraglide/messages';
	interface Props {
		handler: DataHandler;
	}

	let { handler }: Props = $props();
	const rowCount = handler.getRowCount();
</script>

{#if $rowCount === undefined}
	<div></div>
{:else}
	<aside class="text-sm" data-testid="row-count">
		{#if $rowCount?.total > 0}
			{m.rowCount({ start: $rowCount.start, end: $rowCount.end, total: $rowCount.total })}
		{:else}
			{m.noEntriesFound()}
		{/if}
	</aside>
{/if}
