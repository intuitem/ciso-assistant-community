<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';
	import { afterNavigate } from '$app/navigation';
	import { tableStates } from '$lib/utils/stores';
	import { breadcrumbs } from '$lib/utils/breadcrumbs';
	interface Props {
		handler: DataHandler;
		URLModel: string;
	}

	let { handler, URLModel }: Props = $props();

	const pageNumber = handler.getPageNumber();
	const rowsPerPage = handler.getRowsPerPage();
	const pageCount = handler.getPageCount();
	const pages = handler.getPages({ ellipsis: true });

	const setPage = (value: 'previous' | 'next' | number) => {
		handler.setPage(value);
		$tableStates[page.url.pathname] = {
			pageNumber: $pageNumber,
			rowsPerPage: $rowsPerPage as number
		};
		page.url.searchParams.set('page', $pageNumber.toString());
		const fullPath = page.url.pathname + page.url.search;
		const hrefPattern = new RegExp(`^/${URLModel}(\\?.*)?$`);
		if (hrefPattern.test(fullPath)) {
			breadcrumbs.updateCrumb(hrefPattern, { href: fullPath });
		}
		handler.invalidate();
	};

	let currentEndpoint: string | null = $state(null);

	afterNavigate(() => {
		if (page.url && page.url.pathname !== currentEndpoint) {
			const endpoint = page.url.pathname;
			let newPageNumber = parseInt(page.url.searchParams.get('page') ?? '1');
			setTimeout(() => {
				handler.setPage(newPageNumber);
				handler.invalidate();
			}, 300);
			currentEndpoint = endpoint;
		}
	});
</script>

<section class="flex">
	<button type="button" class:disabled={$pageNumber === 1} onclick={() => setPage('previous')}>
		{m.previous()}
	</button>
	{#if $pages === undefined}
		<button type="button" onclick={() => setPage($pageNumber)}>
			{$pageNumber}
		</button>
	{:else}
		{#each $pages as page}
			<button
				type="button"
				class:active={$pageNumber === page}
				class:ellipse={page === null}
				onclick={() => setPage(page)}
			>
				{page ?? '...'}
			</button>
		{/each}
	{/if}
	<button type="button" class:disabled={$pageNumber === $pageCount} onclick={() => setPage('next')}>
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
