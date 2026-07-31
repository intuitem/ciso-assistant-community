<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	export interface MatrixColumn {
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
		groups: string[];
		is_deprecated?: boolean;
		children?: MatrixCell[];
	}

	interface Props {
		columns: MatrixColumn[];
		cells: MatrixCell[];
		facets?: MatrixFacet[];
		/** Link target for a cell. Omit to render cells as plain text. */
		href?: (cell: MatrixCell) => string;
	}

	let { columns, cells, facets = [], href }: Props = $props();

	let activeFacets = $state<string[]>([]);
	let expanded = $state<Record<string, boolean>>({});
	let query = $state('');

	// Facets are OR within a dimension, AND across dimensions: picking two
	// platforms widens, picking a platform and a maturity narrows.
	const facetsByDimension = $derived(
		facets.reduce<Record<string, MatrixFacet[]>>((acc, facet) => {
			const dimension = facet.dimension ?? 'other';
			(acc[dimension] ??= []).push(facet);
			return acc;
		}, {})
	);

	function matches(cell: MatrixCell): boolean {
		const needle = query.trim().toLowerCase();
		if (needle && !`${cell.ref_id} ${cell.name}`.toLowerCase().includes(needle)) {
			// A parent stays visible when one of its sub-techniques matches.
			if (!(cell.children ?? []).some((child) => matches(child))) return false;
		}
		for (const [dimension, group] of Object.entries(facetsByDimension)) {
			const selected = group.filter((facet) => activeFacets.includes(facet.ref_id));
			if (!selected.length) continue;
			if (!selected.some((facet) => cell.groups.includes(facet.ref_id))) return false;
		}
		return true;
	}

	const grid = $derived(
		columns.map((column) => ({
			column,
			items: cells.filter((cell) => cell.groups.includes(column.ref_id) && matches(cell))
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

	<!-- The grid is the wide element, so it owns the horizontal scroll. -->
	<div class="overflow-x-auto pb-2">
		<div class="flex items-start gap-2 min-w-max">
			{#each grid as { column, items } (column.ref_id)}
				<div class="flex w-56 shrink-0 flex-col gap-1">
					<div
						class="rounded-t bg-surface-200-800 px-2 py-2 text-center"
						title={column.description ?? column.name}
					>
						<p class="text-sm font-semibold leading-tight">{column.name}</p>
						<p class="text-xs text-surface-600-400">{items.length}</p>
					</div>
					{#each items as cell (cell.id)}
						{@const children = cell.children ?? []}
						<!-- Keyed by column too: a technique can sit in several tactics, and
						     keying on cell.id alone expands every copy at once. -->
						{@const cellKey = `${column.ref_id}:${cell.id}`}
						{@const isOpen = expanded[cellKey] ?? false}
						<div
							class="rounded border border-surface-300-700 bg-surface-50-950 px-2 py-1 text-xs hover:border-primary-500"
							class:opacity-50={cell.is_deprecated}
						>
							<div class="flex items-start gap-1">
								{#if href}
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
										<li class="leading-snug">
											{#if href}
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
