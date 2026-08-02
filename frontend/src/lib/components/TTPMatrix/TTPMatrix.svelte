<script lang="ts">
	import { untrack } from 'svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	export interface MatrixColumn {
		id: string;
		ref_id: string;
		name: string;
		description?: string;
	}

	export interface MatrixFacet {
		ref_id: string;
		name: string;
		dimension?: string;
	}

	export interface MatrixCell {
		id: string;
		ref_id: string;
		name: string;
		tactics: string[];
		groups: string[];
		children?: MatrixCell[];
	}

	interface Props {
		columns: MatrixColumn[];
		cells: MatrixCell[];
		facets?: MatrixFacet[];
		/** Link target for a cell. Omit to render cells as plain text. */
		href?: (cell: MatrixCell) => string;
		/** Selection mode: cells become toggles instead of links. */
		selectable?: boolean;
		/** Keys are `techniqueId:tacticId` — the same technique in two columns is two cells. */
		selected?: Set<string>;
		onToggle?: (cell: MatrixCell, column: MatrixColumn) => void;
	}

	let {
		columns,
		cells,
		facets = [],
		href,
		selectable = false,
		selected = new Set<string>(),
		onToggle
	}: Props = $props();

	let activeFacets = $state<string[]>([]);
	let expanded = $state<Record<string, boolean>>({});
	let query = $state('');

	// the component is reused across catalogs, so filters must not carry over
	$effect(() => {
		void columns;
		void cells;
		untrack(() => {
			activeFacets = [];
			expanded = {};
			query = '';
		});
	});

	// OR within a dimension, AND across dimensions
	const facetsByDimension = $derived(
		facets.reduce<Record<string, MatrixFacet[]>>((acc, facet) => {
			const dimension = facet.dimension ?? 'other';
			(acc[dimension] ??= []).push(facet);
			return acc;
		}, {})
	);

	// both filters keep a parent whose sub-technique matches, so a cell never
	// disappears because only its children qualify
	function matchesSelf(cell: MatrixCell): boolean {
		const needle = query.trim().toLowerCase();
		if (needle && !`${cell.ref_id} ${cell.name}`.toLowerCase().includes(needle)) return false;
		for (const [dimension, group] of Object.entries(facetsByDimension)) {
			const selected = group.filter((facet) => activeFacets.includes(facet.ref_id));
			if (!selected.length) continue;
			if (!selected.some((facet) => cell.groups.includes(facet.ref_id))) return false;
		}
		return true;
	}

	function matches(cell: MatrixCell): boolean {
		return matchesSelf(cell) || (cell.children ?? []).some((child) => matchesSelf(child));
	}

	const grid = $derived(
		columns.map((column) => ({
			column,
			items: cells.filter((cell) => cell.tactics.includes(column.id) && matches(cell))
		}))
	);

	const total = $derived(grid.reduce((sum, entry) => sum + entry.items.length, 0));

	function toggleFacet(refId: string) {
		activeFacets = activeFacets.includes(refId)
			? activeFacets.filter((value) => value !== refId)
			: [...activeFacets, refId];
	}
</script>

<div class="flex flex-col gap-4">
	<div class="flex flex-wrap items-center gap-3">
		<input
			type="search"
			class="input max-w-xs"
			placeholder={m.search()}
			bind:value={query}
			aria-label={m.search()}
		/>
		{#each Object.entries(facetsByDimension) as [dimension, group] (dimension)}
			<div class="flex flex-wrap items-center gap-1">
				<span class="text-xs uppercase tracking-wide text-surface-600-400"
					>{safeTranslate(dimension)}</span
				>
				{#each group as facet (facet.ref_id)}
					{@const active = activeFacets.includes(facet.ref_id)}
					<button
						type="button"
						class="badge {active ? 'preset-filled-primary-500' : 'preset-tonal-surface'}"
						aria-pressed={active}
						onclick={() => toggleFacet(facet.ref_id)}
					>
						{facet.name}
					</button>
				{/each}
			</div>
		{/each}
		{#if activeFacets.length || query}
			<button
				type="button"
				class="btn btn-sm preset-tonal-surface"
				onclick={() => {
					activeFacets = [];
					query = '';
				}}
			>
				{m.clearFilters()}
			</button>
		{/if}
		<span class="ml-auto text-sm text-surface-600-400">{total}</span>
	</div>

	<div class="overflow-x-auto pb-2">
		<div class="flex items-start gap-2 min-w-max">
			{#each grid as { column, items } (column.ref_id)}
				<div class="flex w-56 shrink-0 flex-col gap-1">
					<!-- fixed height: a name that wraps to two lines (common in French)
					     would otherwise push its column's cells out of alignment -->
					<div
						class="flex min-h-[4.25rem] flex-col items-center justify-center rounded-t bg-surface-200-800 px-2 py-2 text-center"
						title={column.description ?? column.name}
					>
						<p class="text-sm font-semibold leading-tight">{column.name}</p>
						<p class="text-xs text-surface-600-400">{items.length}</p>
					</div>
					{#each items as cell (cell.id)}
						{@const children = cell.children ?? []}
						<!-- keyed by column: a technique can sit in several tactics -->
						{@const cellKey = `${column.ref_id}:${cell.id}`}
						{@const isOpen = expanded[cellKey] ?? false}
						<div
							class="rounded border px-2 py-1 text-xs hover:border-primary-500 {selectable &&
							selected.has(`${cell.id}:${column.id}`)
								? 'border-primary-500 bg-primary-500/15'
								: 'border-surface-300-700 bg-surface-50-950'}"
						>
							<div class="flex items-start gap-1">
								{#if selectable}
									<button
										type="button"
										class="grow text-left leading-snug"
										aria-pressed={selected.has(`${cell.id}:${column.id}`)}
										onclick={() => onToggle?.(cell, column)}
									>
										{cell.name}
									</button>
								{:else if href}
									<a class="anchor grow leading-snug" href={href(cell)}>{cell.name}</a>
								{:else}
									<span class="grow leading-snug">{cell.name}</span>
								{/if}
								{#if children.length}
									<button
										type="button"
										class="shrink-0 text-surface-600-400 hover:text-primary-500"
										aria-expanded={isOpen}
										aria-label={cell.name}
										onclick={() => (expanded[cellKey] = !isOpen)}
									>
										<i class="fa-solid {isOpen ? 'fa-caret-down' : 'fa-caret-right'}"></i>
										<span class="text-[10px]">{children.length}</span>
									</button>
								{/if}
							</div>
							{#if isOpen}
								<ul class="mt-1 space-y-0.5 border-t border-surface-300-700 pt-1 pl-2">
									{#each children as child (child.id)}
										<li
											class="leading-snug {selectable && selected.has(`${child.id}:${column.id}`)
												? 'rounded bg-primary-500/15 px-1 font-medium'
												: ''}"
										>
											{#if selectable}
												<button
													type="button"
													class="w-full text-left"
													aria-pressed={selected.has(`${child.id}:${column.id}`)}
													onclick={() => onToggle?.(child, column)}
												>
													{child.name}
												</button>
											{:else if href}
												<a class="anchor" href={href(child)}>{child.name}</a>
											{:else}
												{child.name}
											{/if}
										</li>
									{/each}
								</ul>
							{/if}
						</div>
					{/each}
				</div>
			{/each}
		</div>
	</div>
</div>
