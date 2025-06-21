<script lang="ts">
	import { run } from 'svelte/legacy';

	import type { DataHandler } from '@vincjo/datatables/remote';
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		handler: DataHandler;
	}

	let { handler }: Props = $props();

	const pageNumber = handler.getPageNumber();
	const rowsPerPage = handler.getRowsPerPage();
	const rowCount = handler.getRowCount();

	let lastRowsPerPage = $derived($rowsPerPage ?? 10);

	const setPage = (value: 'previous' | 'next' | number) => {
		handler.setPage(value);
		handler.invalidate();
	};

	const setRowsPerPage = () => {
		const pageNumberCache: { [key: string]: [number, number] } = JSON.parse(
			localStorage.getItem('pageNumberCache') ?? '{}'
		);

		for (const [endpoint, [savedPageNumber, savedRowsPerPage]] of Object.entries(pageNumberCache)) {
			if ($rowsPerPage === null) {
				break;
			}
			const itemNumber = (savedPageNumber - 1) * savedRowsPerPage + 1;
			const newPageNumber = Math.ceil(itemNumber / $rowsPerPage);
			pageNumberCache[endpoint] = [newPageNumber, $rowsPerPage];
		}

		localStorage.setItem('pageNumberCache', JSON.stringify(pageNumberCache));
		localStorage.setItem('rowsPerPageCache', `${$rowsPerPage}`);

		const itemNumber = ($pageNumber - 1) * lastRowsPerPage + 1;
		const newPageNumber = Math.ceil(itemNumber / ($rowsPerPage ?? 10));
		setPage(newPageNumber);
	};

	run(() => {
		if ($rowsPerPage && $rowCount?.start >= $rowCount?.total) {
			setPage(Math.ceil($rowCount.total / $rowsPerPage));
		}
	});

	onMount(() => {
		const cachedValue = Number(localStorage.getItem('rowsPerPageCache') ?? '10');

		if ($rowsPerPage !== cachedValue) {
			rowsPerPage.set(cachedValue); // will trigger reactivity
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
