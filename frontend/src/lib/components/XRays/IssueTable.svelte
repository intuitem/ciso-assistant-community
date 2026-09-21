<script lang="ts">
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import { ISSUE_COLUMNS, formatCell, type Issue } from './utils';

	interface Props {
		issue: Issue;
		rowsPerPage?: number;
	}

	let { issue, rowsPerPage = 10 }: Props = $props();

	let pageNumber = $state(1);
	let search = $state('');

	const columns = $derived(ISSUE_COLUMNS[issue.objType] ?? []);

	// Matches the name and every metadata column, as the cells render them.
	const matches = $derived(
		search.trim() === ''
			? issue.occurrences
			: issue.occurrences.filter((occurrence) => {
					const haystack = [
						occurrence.name,
						...columns.map((column) => formatCell(occurrence.object?.[column.key], column.kind))
					]
						.join(' ')
						.toLowerCase();
					return haystack.includes(search.trim().toLowerCase());
				})
	);

	const pageCount = $derived(Math.max(1, Math.ceil(matches.length / rowsPerPage)));
	const currentPage = $derived(Math.min(pageNumber, pageCount));
	const offset = $derived((currentPage - 1) * rowsPerPage);
	const rows = $derived(matches.slice(offset, offset + rowsPerPage));
</script>

{#if issue.occurrences.length > rowsPerPage}
	<div class="px-2 pt-2">
		<input
			class="input bg-surface-50-950 max-w-xs text-xs"
			type="search"
			placeholder={m.searchPlaceholder()}
			bind:value={search}
			oninput={() => (pageNumber = 1)}
		/>
	</div>
{/if}

<table class="table table-interactive text-xs">
	<thead class="table-head">
		<tr>
			<th class="w-8 font-normal text-surface-500">#</th>
			<th>{m.name()}</th>
			{#each columns as column (column.key)}
				<th class="w-32">{column.label()}</th>
			{/each}
		</tr>
	</thead>
	<tbody>
		{#each rows as row, index (`${row.link}-${index}`)}
			<tr>
				<td class="text-surface-400-600 font-mono">{offset + index + 1}</td>
				<td>
					<Anchor class="anchor" href={row.link}>{row.name || m.xRaysView()}</Anchor>
				</td>
				{#each columns as column (column.key)}
					<td class="text-surface-600-400">{formatCell(row.object?.[column.key], column.kind)}</td>
				{/each}
			</tr>
		{/each}
		{#if rows.length === 0}
			<tr>
				<td colspan={columns.length + 2} class="text-surface-500 py-3 text-center">
					{m.noResults()}
				</td>
			</tr>
		{/if}
	</tbody>
</table>

{#if pageCount > 1 || matches.length !== issue.occurrences.length}
	<div class="flex items-center gap-3 px-2 py-2 text-xs text-surface-600-400">
		<span>
			{matches.length === 0 ? 0 : offset + 1}-{offset + rows.length} / {matches.length}
		</span>
		{#if pageCount > 1}
			<div class="ml-auto flex items-center gap-1">
				<button
					type="button"
					class="btn btn-sm preset-outlined-surface-500 text-xs"
					disabled={currentPage <= 1}
					onclick={() => (pageNumber = Math.max(1, currentPage - 1))}
				>
					{m.previous()}
				</button>
				<span class="px-2">{currentPage} / {pageCount}</span>
				<button
					type="button"
					class="btn btn-sm preset-outlined-surface-500 text-xs"
					disabled={currentPage >= pageCount}
					onclick={() => (pageNumber = Math.min(pageCount, currentPage + 1))}
				>
					{m.next()}
				</button>
			</div>
		{/if}
	</div>
{/if}
