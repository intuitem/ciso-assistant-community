<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables';
	export let handler: DataHandler;
	export let filterBy = '';
	let value = '';
</script>

<th class="{$$props.class} !py-0">
	<input
		type="text"
		class="input variant-form-material placeholder:text-xs bg-transparent p-0"
		placeholder="Filter"
		bind:value
		on:input={() => handler.filter(value, filterBy)}
	/>
</th>
