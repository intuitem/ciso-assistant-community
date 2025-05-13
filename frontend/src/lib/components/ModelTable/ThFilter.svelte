<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables/remote';
	interface Props {
		handler: DataHandler;
		filterBy?: string;
	}

	let { handler, filterBy = '' }: Props = $props();
	let value = $state('');
	let classProp = ''; // Replacing $$props.class
</script>

<th class="{classProp} !py-0">
	<input
		type="text"
		class="input variant-form-material placeholder:text-xs bg-transparent p-0"
		placeholder="Filter {filterBy}..."
		aria-label="Filter by {filterBy}"
		role="searchbox"
		bind:value
		oninput={() => {
			const debounceTimeout = setTimeout(() => {
				handler.filter(value, filterBy);
			}, 300);
			return () => clearTimeout(debounceTimeout);
		}}
	/>
</th>
