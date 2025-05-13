<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables/remote';
	interface Props {
		handler: DataHandler;
		orderBy?: string;
		_class?: any;
		children?: import('svelte').Snippet;
		[key: string]: any
	}

	let {
		handler,
		orderBy = '',
		_class = `${rest.class} cursor-pointer select-none`,
		children,
		...rest
	}: Props = $props();

	const identifier = orderBy?.toString();

	const sort = handler.getSort();
	const update = () => {
		handler.sort(orderBy);
		handler.invalidate();
	};
</script>

<th
	onclick={update}
	class:active={$sort?.orderBy === identifier}
	class={_class}
	data-testid="tableheader"
	role="columnheader"
	aria-sort={$sort?.orderBy === identifier
		? $sort?.direction === 'asc'
			? 'ascending'
			: 'descending'
		: 'none'}
>
	<div class="flex items-center h-full">
		{@render children?.()}
		<span
			class="pl-2"
			class:asc={$sort?.direction === 'asc'}
			class:desc={$sort?.direction === 'desc'}
			aria-hidden="true"
		></span>
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
