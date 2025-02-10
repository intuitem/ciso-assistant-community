<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables';
	export let handler: DataHandler;
	export let orderBy = '';
	export let _class = `${$$restProps.class} cursor-pointer select-none`;

	const identifier = orderBy?.toString();
	const sort = handler.getSort();
</script>

<th
	on:click={() => handler.sort(orderBy)}
	class:active={$sort.identifier === identifier}
	class={_class}
	data-testid="tableheader"
	role="columnheader"
	aria-sort={$sort?.identifier === identifier
		? $sort?.direction === 'asc'
			? 'ascending'
			: 'descending'
		: 'none'}
>
	<div class="flex items-center h-full">
		<slot />
		<span
			class="pl-2"
			class:asc={$sort.direction === 'asc'}
			class:desc={$sort.direction === 'desc'}
			aria-hidden="true"
		/>
	</div>
</th>

<style>
	th span:before,
	th span:after {
		border: 4px solid transparent;
		content: '';
		display: block;
		height: 0;
		width: 0;
	}
	th span:before {
		@apply border-b-surface-200 mt-0.5;
	}
	th span:after {
		@apply border-t-surface-200 mt-0.5;
	}
	th.active span.asc:before {
		@apply border-b-surface-700;
	}
	th.active span.desc:after {
		@apply border-t-surface-700;
	}
</style>
