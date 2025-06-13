<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { m } from '$paraglide/messages';

	export let handler: DataHandler;

	const endpoint = $page.url.pathname;

	const pageNumber = handler.getPageNumber();
	const rowsPerPage = handler.getRowsPerPage();
	const rowCount = handler.getRowCount();

	$: lastRowsPerPage = $rowsPerPage ?? 10;

	const setRowsPerPage = () => {
		const paginationSettingsCache: { [key: string]: [number, number] } = JSON.parse(
			localStorage.getItem('paginationSettingsCache') ?? '{}'
		);

		if ($rowsPerPage !== null) {
			paginationSettingsCache[endpoint] = [paginationSettingsCache[endpoint][0], $rowsPerPage];
		}

		localStorage.setItem('paginationSettingsCache', JSON.stringify(paginationSettingsCache));

		const itemNumber = ($pageNumber - 1) * lastRowsPerPage + 1;
		const newPageNumber = Math.ceil(itemNumber / ($rowsPerPage ?? 10));
		handler.setPage(newPageNumber);
		// console.log('2');
		handler.invalidate();
	};

	$: if ($rowsPerPage && $rowCount?.start >= $rowCount?.total) {
		handler.setPage(Math.ceil($rowCount.total / $rowsPerPage));
	}

	onMount(() => {
		let cachedValue = 10;
		const paginationSettingsCache: { [key: string]: [number, number] } = JSON.parse(
			localStorage.getItem('paginationSettingsCache') ?? '{}'
		);
		if (paginationSettingsCache[endpoint] !== undefined) {
			cachedValue = Number(paginationSettingsCache[endpoint][1] ?? '10');
		}

		if ($rowsPerPage !== cachedValue) {
			rowsPerPage.set(cachedValue); // will trigger reactivity
			// console.log('3');
			handler.invalidate(); // refetch with updated rowsPerPage
		}
	});

	const options = [5, 10, 20, 50, 100];
</script>

<aside class="flex items-center">
	{m.show()}
	<select
		class="select bg-surface-50 w-fit mx-1"
		bind:value={$rowsPerPage}
		on:change={setRowsPerPage}
	>
		{#each options as option}
			<option value={option}>
				{option}
			</option>
		{/each}
	</select>
	{m.entries()}
</aside>
