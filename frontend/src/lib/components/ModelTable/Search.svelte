<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables';
	export let handler: DataHandler;
	let value = '';
</script>

<input
	class="input bg-surface-50 max-w-2xl"
	placeholder="Search..."
	bind:value
	on:input={() => handler.search(value)}
/>
