<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import * as m from '$paraglide/messages';

	export let handler: DataHandler;
	const pageNumber = handler.getPageNumber();
	const pageCount = handler.getPageCount();
	const pages = handler.getPages({ ellipsis: true });
	let urlModel: string | undefined;
	let _sessionStorage = null;

	onMount(() => {
		_sessionStorage = sessionStorage;
	});

	$: if ($page.url && _sessionStorage) {
		const pageData = JSON.parse(_sessionStorage.getItem('model_table_page_data') ?? '{}');
		urlModel = `${$page.url}`.replace('//+$/', '').split('/').pop();

		const currentPage = pageData[urlModel] ?? 1;
		handler.setPage(currentPage);
		pageData[urlModel] = currentPage;

		_sessionStorage.setItem('model_table_page_data', JSON.stringify(pageData));
	}

	$: if ($pageNumber && urlModel && _sessionStorage) {
		const pageData = JSON.parse(_sessionStorage.getItem('model_table_page_data') ?? '{}');
		pageData[urlModel] = $pageNumber;
		_sessionStorage.setItem('model_table_page_data', JSON.stringify(pageData));
	}
</script>

<section class="flex">
	<button
		type="button"
		class:disabled={$pageNumber === 1}
		on:click={() => handler.setPage('previous')}
	>
		{m.previous()}
	</button>
	{#each $pages as page}
		<button
			type="button"
			class:active={$pageNumber === page}
			class:ellipse={page === null}
			on:click={() => handler.setPage(page)}
		>
			{page ?? '...'}
		</button>
	{/each}
	<button
		type="button"
		class:disabled={$pageNumber === $pageCount}
		on:click={() => handler.setPage('next')}
	>
		{m.next()}
	</button>
</section>

<style>
	button {
		background: inherit;
		height: 32px;
		width: 32px;
		color: #616161;
		cursor: pointer;
		font-size: 13px;
		margin: 0;
		padding: 0;
		transition: all, 0.2s;
		line-height: 32px;
		border: 1px solid #e0e0e0;
		border-right: none;
		outline: none;
	}
	button:first-child {
		border-radius: 4px 0 0 4px;
		width: auto;
		min-width: 72px;
	}
	button:last-child {
		border-right: 1px solid #e0e0e0;
		border-radius: 0 4px 4px 0;
		width: auto;
		min-width: 72px;
	}
	button:not(.active):hover {
		background: #eee;
	}
	button.ellipse:hover {
		background: inherit;
		cursor: default;
	}
	button.active {
		background: #eee;
		font-weight: bold;
		cursor: default;
	}
	button.disabled:hover {
		background: inherit;
		cursor: default;
	}
</style>
