<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';
	import { tableStates } from '$lib/utils/stores';
	import { page } from '$app/state';

	interface Props {
		handler: DataHandler;
	}

	let { handler }: Props = $props();

	const pageNumber = handler.getPageNumber();
	const rowsPerPage = handler.getRowsPerPage();
	const rowCount = handler.getRowCount();

	let lastRowsPerPage = $derived(
		$rowsPerPage ?? $tableStates[page.url.pathname]?.rowsPerPage ?? 10
	);

	const setRowsPerPage = () => {
		const itemNumber = ($pageNumber - 1) * lastRowsPerPage + 1;
		const newPageNumber = Math.ceil(itemNumber / ($rowsPerPage ?? 10));
		$tableStates[page.url.pathname] = { pageNumber: newPageNumber, rowsPerPage: $rowsPerPage };
		handler.setPage(newPageNumber);

		handler.invalidate();
	};

	$effect(() => {
		if ($rowsPerPage && $rowCount?.start >= $rowCount?.total) {
			handler.setPage(Math.ceil($rowCount.total / $rowsPerPage));
		}
	});

	onMount(() => {
		const cachedValue = $tableStates[page.url.pathname]?.rowsPerPage ?? 10;

		if ($rowsPerPage !== cachedValue) {
			rowsPerPage.set(cachedValue); // will trigger reactivity
		}
	});

	const options = [5, 10, 20, 50, 100];
</script>

<aside class="flex items-center">
	{m.show()}
	<select
		class="select bg-surface-50 w-fit mx-1"
		bind:value={$rowsPerPage}
		onchange={setRowsPerPage}
	>
		{#each options as option}
			<option value={option}>
				{option}
			</option>
		{/each}
	</select>
	{m.entries()}
</aside>
