<script lang="ts">
	import { page } from '$app/state';
	import { onMount, tick, type Snippet } from 'svelte';
	import { m } from '#paraglide/messages.js';
	import {
		selectionParams,
		type FacetOption,
		type RelatedFilter,
		type RelatedOptionsPage
	} from '#lib/utils/scenarioSelection.js';

	interface Props {
		riskAssessmentId: string;
		name: RelatedFilter;
		/** Draws one option: the bar owns the row and what ticking it does. */
		option: Snippet<[FacetOption]>;
	}

	let { riskAssessmentId, name, option }: Props = $props();

	const PAGE_SIZE = 25;
	const SEARCH_THRESHOLD = 8;
	const SEARCH_DELAY = 250;

	// Read once, when the filter opens. Counts ignore this filter's own values,
	// so ticking one changes nothing here, and following the URL would reorder
	// the pages already listed (applied values come first).
	const selectionQuery = selectionParams(page.url.searchParams).toString();

	let options: FacetOption[] = $state([]);
	let total = $state(0);
	let searchable = $state(false);
	let query = $state('');
	let status: 'loading' | 'ready' | 'failed' = $state('loading');
	let failedOffset = 0;
	let latest = 0;
	let list: HTMLUListElement | undefined = $state();
	let timer: ReturnType<typeof setTimeout> | undefined;

	async function load(offset: number) {
		const request = ++latest;
		const q = query.trim();
		const params = new URLSearchParams(selectionQuery);
		params.set('filter', name);
		params.set('limit', String(PAGE_SIZE));
		params.set('offset', String(offset));
		if (q) params.set('q', q);
		status = 'loading';
		try {
			const res = await fetch(
				`/risk-assessments/${riskAssessmentId}/scenario-selection/options?${params}`
			);
			if (!res.ok) throw new Error(res.statusText);
			const body: RelatedOptionsPage = await res.json();
			// A slow answer to an older search must not replace a newer one.
			if (request !== latest) return;
			options =
				offset === 0
					? body.results
					: [
							...options,
							...body.results.filter((o) => !options.some((known) => known.value === o.value))
						];
			total = body.count;
			if (offset === 0 && !q) searchable = body.count > SEARCH_THRESHOLD;
			status = 'ready';
			if (offset > 0) {
				// "Load more" leaves the list once its page arrives: hand the keyboard
				// to the first option it brought rather than dropping focus.
				await tick();
				list?.querySelectorAll('li')[offset]?.querySelector('input')?.focus();
			}
		} catch {
			if (request !== latest) return;
			failedOffset = offset;
			status = 'failed';
		}
	}

	function search() {
		clearTimeout(timer);
		timer = setTimeout(() => load(0), SEARCH_DELAY);
	}

	onMount(() => {
		load(0);
		return () => clearTimeout(timer);
	});
</script>

{#if searchable}
	<label class="block px-1 pt-1 pb-1.5">
		<span class="sr-only">{m.search()}</span>
		<input
			type="search"
			class="input text-sm"
			placeholder={m.searchPlaceholder()}
			bind:value={query}
			oninput={search}
			{@attach (el) => el.focus()}
		/>
	</label>
{/if}
<ul
	bind:this={list}
	class="max-h-72 overflow-y-auto"
	aria-busy={status === 'loading'}
	data-testid="selection-related-options"
>
	{#each options as item (item.value)}
		<li>{@render option(item)}</li>
	{/each}
	{#if status === 'loading'}
		<li class="flex items-center gap-2.5 min-h-10 px-2.5 text-sm text-surface-500" role="status">
			<i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i>
			{m.loading()}
		</li>
	{:else if status === 'failed'}
		<li class="flex items-center justify-between gap-2.5 min-h-10 px-2.5 text-sm" role="alert">
			<span class="text-error-700 dark:text-error-300">{m.anErrorOccurred()}</span>
			<button type="button" class="anchor" onclick={() => load(failedOffset)}>{m.retry()}</button>
		</li>
	{:else if options.length === 0}
		<li class="px-2.5 py-2 text-sm text-surface-500">{m.noResults()}</li>
	{:else if options.length < total}
		<li>
			<button
				type="button"
				class="w-full flex items-center justify-between gap-2.5 min-h-10 px-2.5 rounded-md text-sm font-medium text-primary-700 dark:text-primary-200 hover:bg-primary-500/10 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary-500"
				onclick={() => load(options.length)}
				data-testid="selection-load-more"
			>
				{m.loadMoreOptions()}
				<span class="tabular-nums font-normal text-surface-500">{options.length} / {total}</span>
			</button>
		</li>
	{/if}
</ul>
