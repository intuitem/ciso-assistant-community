<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables/remote';
	interface Props {
		handler: DataHandler;
		orderBy?: string;
		_class?: any;
		children?: import('svelte').Snippet;
		[key: string]: any;
	}

	let {
		handler,
		orderBy = '',
		_class = 'cursor-pointer select-none ',
		children,
		...rest
	}: Props = $props();

	_class += rest.class;

	const identifier = orderBy?.toString();
	const sortable = Boolean(orderBy);

	const sort = handler.getSort();
	const update = () => {
		handler.sort(orderBy);
		handler.invalidate();
	};

	let isActive = $derived($sort?.orderBy === identifier);
</script>

<th
	class:active={isActive}
	class="{_class} hover:text-surface-950-50"
	data-testid="tableheader"
	role="columnheader"
	aria-sort={$sort?.orderBy === identifier
		? $sort?.direction === 'asc'
			? 'ascending'
			: 'descending'
		: 'none'}
>
	{#snippet label()}
		{@render children?.()}
		<span
			class="pl-2 before:border-b-surface-200-800 before:mt-0.5 after:border-t-surface-200-800 after:mt-0.5"
			class:asc={$sort?.direction === 'asc'}
			class:desc={$sort?.direction === 'desc'}
			aria-hidden="true"
		>
			{#if isActive && $sort?.direction === 'asc'}
				<i class="fa-solid fa-sort-up"></i>
			{:else if isActive && $sort?.direction === 'desc'}
				<i class="fa-solid fa-sort-down"></i>
			{/if}
		</span>
	{/snippet}

	{#if sortable}
		<button
			type="button"
			onclick={update}
			class="flex items-center h-full w-full cursor-pointer text-left"
		>
			{@render label()}
		</button>
	{:else}
		<div class="flex items-center h-full">
			{@render label()}
		</div>
	{/if}
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
</style>
