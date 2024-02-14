<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables';
	export let handler: DataHandler;
	let value = '';
</script>

<input
	class="input bg-surface-50 max-w-2xl"
	data-testid="search-input"
	placeholder="Search..."
	bind:value
	on:input={() => handler.search(value)}
/>
