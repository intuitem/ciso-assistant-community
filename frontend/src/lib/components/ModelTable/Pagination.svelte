<script lang="ts">
	import type { DataHandler } from '@vincjo/datatables/remote';
	import { page } from '$app/stores';
	import { m } from '$paraglide/messages';
	import { afterNavigate } from '$app/navigation';
	export let handler: DataHandler;

	const pageNumber = handler.getPageNumber();
	const pageCount = handler.getPageCount();
	const pages = handler.getPages({ ellipsis: true });

	const setPage = (value: 'previous' | 'next' | number) => {
		handler.setPage(value);
		handler.invalidate();
	};

	afterNavigate(() => {
		if ($page.url) {
			handler.setPage(1);
		}
	});
</script>

<section class="flex">
	<button type="button" class:disabled={$pageNumber === 1} on:click={() => setPage('previous')}>
		{m.previous()}
	</button>
	{#if $pages === undefined}
		<button type="button" on:click={() => setPage($pageNumber)}>
			{$pageNumber}
		</button>
	{:else}
		{#each $pages as page}
			<button
				type="button"
				class:active={$pageNumber === page}
				class:ellipse={page === null}
				on:click={() => setPage(page)}
			>
				{page ?? '...'}
			</button>
		{/each}
	{/if}
	<button
		type="button"
		class:disabled={$pageNumber === $pageCount}
		on:click={() => setPage('next')}
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
