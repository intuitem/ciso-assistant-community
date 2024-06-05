<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables';
	import * as m from '$paraglide/messages';
	export let handler: DataHandler;
	const rowCount = handler.getRowCount();
</script>

<aside class="text-sm">
	{#if $rowCount.total > 0}
		{m.rowCount({ start: $rowCount.start, end: $rowCount.end, total: $rowCount.total })}
	{:else}
		{m.noEntriesFound()}
	{/if}
</aside>
