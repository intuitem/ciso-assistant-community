<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables';
	export let handler: DataHandler;
	export let orderBy = '';
	export let _class = `${$$restProps.class} cursor-pointer select-none`;

	const identifier = orderBy?.toString();
	const sorted = handler.getSort();
</script>

<th
	on:click={() => handler.sort(orderBy)}
	class:active={$sorted.identifier === identifier}
	class={_class}
	data-testid="tableheader"
>
	<div class="flex items-center h-full">
		<slot />
		<span
			class="pl-2"
			class:asc={$sorted.direction === 'asc'}
			class:desc={$sorted.direction === 'desc'}
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
