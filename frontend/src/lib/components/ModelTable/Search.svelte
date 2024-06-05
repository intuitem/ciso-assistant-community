<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables';
	import * as m from '$paraglide/messages';
	export let handler: DataHandler;
	let value = '';
</script>

<input
	class="input bg-surface-50 max-w-2xl"
	placeholder={m.searchPlaceholder()}
	data-testid="search-input"
	bind:value
	on:input={() => handler.search(value)}
/>
