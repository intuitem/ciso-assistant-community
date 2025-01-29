<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables';
	export let handler: DataHandler;
	export let filterBy = '';
	let value = '';
	let classProp = ''; // Replacing $$props.class
</script>

<th class="{classProp} !py-0">
	<input
		type="text"
		class="input variant-form-material placeholder:text-xs bg-transparent p-0"
		placeholder="Filter"
		bind:value
		on:input={() => handler.filter(value, filterBy)}
	/>
</th>
