<script lang="ts">
	import SegmentedControl from '$lib/components/Forms/SegmentedControl.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';
	import type { MappingRequirement, MappingRow } from './types';
	import {
		aggregateBySide,
		compareValues,
		escapeSpreadsheetFormula,
		filterByCoverage,
		matchesQuery,
		relationshipRank,
		RELATIONSHIP_ORDER,
		type AggregateRow,
		type CoverageFilter,
		type Counterpart,
		type MappingViewMode
	} from './aggregate';

	interface Props {
		rows: MappingRow[];
		sourceRequirements: MappingRequirement[];
		targetRequirements: MappingRequirement[];
		sourceFramework: string;
		targetFramework: string;
	}

	let { rows, sourceRequirements, targetRequirements, sourceFramework, targetFramework }: Props =
		$props();

	const RELATIONSHIP_COLOR: Record<string, string> = {
		equal: 'bg-success-100-900 text-success-900-100',
		superset: 'bg-primary-100-900 text-primary-900-100',
		subset: 'bg-tertiary-100-900 text-tertiary-900-100',
		intersect: 'bg-warning-100-900 text-warning-900-100',
		not_related: 'bg-surface-200-800 text-surface-700-300'
	};

	let mode: MappingViewMode = $state('one_to_one');
	let search = $state('');
	let relationshipFilter = $state('all');
	let coverageFilter: CoverageFilter = $state('all');
	let sortKey = $state('');
	let sortAsc = $state(true);
	let rowsPerPage = $state(25);
	let currentPage = $state(1);

	const modeOptions = $derived([
		{ value: 'one_to_one', label: m.oneToOne() },
		{ value: 'per_source', label: m.aggregatePerSource() },
		{ value: 'per_target', label: m.aggregatePerTarget() }
	]);

	const relationships = $derived.by(() => {
		const present = new Set(rows.map((row) => row.relationship).filter(Boolean));
		return RELATIONSHIP_ORDER.filter((relationship) => present.has(relationship));
	});

	// Libraries fill only some of these; an all-empty column is noise.
	const showAnnotation = $derived(rows.some((row) => row.annotation));
	const showStrength = $derived(rows.some((row) => row.strength_of_relationship != null));
	const showRationale = $derived(rows.some((row) => row.rationale));

	const requirementsByUrn = $derived(
		new Map(
			[...sourceRequirements, ...targetRequirements].map((requirement) => [
				requirement.urn,
				requirement
			])
		)
	);

	// Some requirements carry neither ref_id nor name; without a fallback the row renders blank.
	function refFor(urn: string, refId: string | null): string {
		return refId ?? urn.split(':').pop() ?? '';
	}

	function nameFor(urn: string, name: string | null): string {
		return name ?? requirementsByUrn.get(urn)?.description ?? '';
	}

	// Filtering links empties the groups that had only those links; they then read as unmapped.
	const relationshipFiltered = $derived(
		relationshipFilter === 'all'
			? rows
			: rows.filter((row) => row.relationship === relationshipFilter)
	);

	const filteredRows = $derived.by((): (MappingRow | AggregateRow)[] => {
		const query = search.trim().toLowerCase();

		if (mode === 'one_to_one') {
			if (!query) return relationshipFiltered;
			return relationshipFiltered.filter((row) =>
				matchesQuery(
					[
						refFor(row.source_urn, row.source_ref_id),
						nameFor(row.source_urn, row.source_name),
						refFor(row.target_urn, row.target_ref_id),
						nameFor(row.target_urn, row.target_name),
						row.annotation
					],
					query
				)
			);
		}

		const perSource = mode === 'per_source';
		const aggregated = filterByCoverage(
			aggregateBySide(
				perSource ? sourceRequirements : targetRequirements,
				relationshipFiltered,
				perSource ? 'source' : 'target'
			),
			coverageFilter
		);

		if (!query) return aggregated;
		return aggregated.filter((row) =>
			matchesQuery(
				[
					refFor(row.urn, row.ref_id),
					nameFor(row.urn, row.name),
					...row.counterparts.flatMap((counterpart) => [
						refFor(counterpart.urn, counterpart.ref_id),
						nameFor(counterpart.urn, counterpart.name)
					])
				],
				query
			)
		);
	});

	function sortValue(row: MappingRow | AggregateRow, key: string): string | number | null {
		if (key === 'relationship') return relationshipRank(row.relationship);
		if (key === 'strength_of_relationship') return (row as MappingRow)[key];
		const value = cellValue(row, key);
		return value == null || value === '' ? null : (value as string | number);
	}

	const visibleRows = $derived.by(() => {
		if (!sortKey) return filteredRows;
		const key = sortKey;
		return [...filteredRows].sort((a, b) => {
			const result = compareValues(sortValue(a, key), sortValue(b, key));
			return sortAsc ? result : -result;
		});
	});

	const pageCount = $derived(Math.max(1, Math.ceil(visibleRows.length / rowsPerPage)));
	const pagedRows = $derived(
		visibleRows.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage)
	);

	// Any change to what is listed invalidates the current page number.
	$effect(() => {
		void [mode, search, relationshipFilter, coverageFilter, rowsPerPage];
		currentPage = 1;
	});

	$effect(() => {
		if (currentPage > pageCount) currentPage = pageCount;
	});

	function toggleSort(key: string) {
		if (sortKey === key) {
			sortAsc = !sortAsc;
		} else {
			sortKey = key;
			sortAsc = true;
		}
	}

	interface Column {
		key: string;
		label: string;
		sortable?: boolean;
	}

	const columns = $derived.by((): Column[] => {
		if (mode === 'one_to_one') {
			return [
				{ key: 'source_ref_id', label: `${m.source()} ${m.refId()}` },
				{ key: 'source_name', label: `${m.source()} ${m.name()}` },
				{ key: 'relationship', label: m.relationship() },
				...(showStrength ? [{ key: 'strength_of_relationship', label: m.strength() }] : []),
				...(showRationale ? [{ key: 'rationale', label: m.rationale() }] : []),
				{ key: 'target_ref_id', label: `${m.target()} ${m.refId()}` },
				{ key: 'target_name', label: `${m.target()} ${m.name()}` },
				...(showAnnotation ? [{ key: 'annotation', label: m.annotation() }] : [])
			];
		}
		const perSource = mode === 'per_source';
		return [
			{ key: 'ref_id', label: `${perSource ? sourceFramework : targetFramework} ${m.refId()}` },
			{ key: 'name', label: m.name() },
			{ key: 'relationship', label: m.relationship() },
			{ key: 'counterparts', label: m.count() },
			{
				key: 'counterparts_list',
				label: perSource ? targetFramework : sourceFramework,
				sortable: false
			}
		];
	});

	// Requirement urns are unique per side; mapping rows repeat, so they key on index.
	function rowKey(row: MappingRow | AggregateRow): string | number {
		return 'urn' in row ? row.urn : row.index;
	}

	function requirementLabel(counterpart: Counterpart): string {
		return [refFor(counterpart.urn, counterpart.ref_id), nameFor(counterpart.urn, counterpart.name)]
			.filter(Boolean)
			.join(' - ');
	}

	function csvCell(value: unknown): string {
		const text = escapeSpreadsheetFormula(value == null ? '' : String(value));
		return /[",\n;]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
	}

	/** Displayed cell value; sorting and CSV export both act on it. */
	function cellValue(row: MappingRow | AggregateRow, key: string): unknown {
		if (key === 'counterparts') return (row as AggregateRow).counterparts.length;
		if (key === 'counterparts_list') {
			return (row as AggregateRow).counterparts.map(requirementLabel).join(' | ');
		}
		if (key === 'ref_id') return refFor((row as AggregateRow).urn, (row as AggregateRow).ref_id);
		if (key === 'name') return nameFor((row as AggregateRow).urn, (row as AggregateRow).name);
		if (key === 'source_ref_id')
			return refFor((row as MappingRow).source_urn, (row as MappingRow).source_ref_id);
		if (key === 'source_name')
			return nameFor((row as MappingRow).source_urn, (row as MappingRow).source_name);
		if (key === 'target_ref_id')
			return refFor((row as MappingRow).target_urn, (row as MappingRow).target_ref_id);
		if (key === 'target_name')
			return nameFor((row as MappingRow).target_urn, (row as MappingRow).target_name);
		if (key === 'relationship' || key === 'rationale') {
			const value = (row as Record<string, any>)[key];
			return value ? safeTranslate(value) : '';
		}
		return (row as Record<string, any>)[key];
	}

	function exportCsv() {
		const lines = [
			columns.map((column) => csvCell(column.label)).join(','),
			...visibleRows.map((row) =>
				columns.map((column) => csvCell(cellValue(row, column.key))).join(',')
			)
		];
		const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
		const url = URL.createObjectURL(blob);
		const anchor = document.createElement('a');
		anchor.href = url;
		anchor.download = `mapping-${mode}.csv`;
		anchor.click();
		URL.revokeObjectURL(url);
	}
</script>

<div class="flex flex-col gap-3 p-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<SegmentedControl
			options={modeOptions}
			value={mode}
			onChange={(value) => (mode = value as MappingViewMode)}
			size="sm"
			ariaLabel={m.viewMode()}
		/>
		<button type="button" class="btn btn-sm preset-tonal-secondary" onclick={exportCsv}>
			<i class="fa-solid fa-file-csv mr-2"></i>{m.exportCsv()}
		</button>
	</div>

	<div class="flex flex-wrap items-center gap-2">
		<input
			type="search"
			class="input w-64"
			placeholder={m.search()}
			bind:value={search}
			aria-label={m.search()}
		/>
		<select class="select w-52" bind:value={relationshipFilter} aria-label={m.relationship()}>
			<option value="all">{m.relationship()}: {m.all()}</option>
			{#each relationships as relationship (relationship)}
				<option value={relationship}>{safeTranslate(relationship)}</option>
			{/each}
		</select>
		{#if mode !== 'one_to_one'}
			<select class="select w-44" bind:value={coverageFilter} aria-label={m.coverage()}>
				<option value="all">{m.coverage()}: {m.all()}</option>
				<option value="mapped">{m.mapped()}</option>
				<option value="unmapped">{m.unmapped()}</option>
			</select>
		{/if}
		<span class="text-sm text-surface-600-400">{visibleRows.length} {m.items()}</span>
	</div>

	<div class="overflow-x-auto rounded-lg ring-1 ring-surface-200-800">
		<table class="w-full text-sm">
			<thead class="bg-surface-100-900 text-left">
				<tr>
					{#each columns as column (column.key)}
						<th class="px-3 py-2 font-semibold whitespace-nowrap">
							{#if column.sortable === false}
								{column.label}
							{:else}
								<button
									type="button"
									class="inline-flex items-center gap-1 hover:text-primary-500"
									onclick={() => toggleSort(column.key)}
								>
									{column.label}
									{#if sortKey === column.key}
										<i class="fa-solid fa-sort-{sortAsc ? 'up' : 'down'} text-xs"></i>
									{/if}
								</button>
							{/if}
						</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each pagedRows as row (rowKey(row))}
					<tr class="border-t border-surface-200-800 align-top hover:bg-surface-50-950">
						{#if mode === 'one_to_one'}
							{@const mapping = row as MappingRow}
							<td class="px-3 py-2 font-mono text-xs whitespace-nowrap"
								>{refFor(mapping.source_urn, mapping.source_ref_id)}</td
							>
							<td class="px-3 py-2">{nameFor(mapping.source_urn, mapping.source_name)}</td>
							<td class="px-3 py-2">
								{#if mapping.relationship}
									<span
										class="rounded-sm px-2 py-0.5 text-xs whitespace-nowrap {RELATIONSHIP_COLOR[
											mapping.relationship
										] ?? ''}"
									>
										{safeTranslate(mapping.relationship)}
									</span>
								{/if}
							</td>
							{#if showStrength}
								<td class="px-3 py-2">{mapping.strength_of_relationship ?? ''}</td>
							{/if}
							{#if showRationale}
								<td class="px-3 py-2"
									>{mapping.rationale ? safeTranslate(mapping.rationale) : ''}</td
								>
							{/if}
							<td class="px-3 py-2 font-mono text-xs whitespace-nowrap"
								>{refFor(mapping.target_urn, mapping.target_ref_id)}</td
							>
							<td class="px-3 py-2">{nameFor(mapping.target_urn, mapping.target_name)}</td>
							{#if showAnnotation}
								<td class="px-3 py-2 text-surface-600-400">{mapping.annotation ?? ''}</td>
							{/if}
						{:else}
							{@const group = row as AggregateRow}
							<td class="px-3 py-2 font-mono text-xs whitespace-nowrap"
								>{refFor(group.urn, group.ref_id)}</td
							>
							<td class="px-3 py-2">{nameFor(group.urn, group.name)}</td>
							<td class="px-3 py-2">
								{#if group.relationship}
									<span
										class="rounded-sm px-2 py-0.5 text-xs whitespace-nowrap {RELATIONSHIP_COLOR[
											group.relationship
										] ?? ''}"
									>
										{safeTranslate(group.relationship)}
									</span>
								{/if}
							</td>
							<td class="px-3 py-2">
								<span
									class="rounded-sm px-2 py-0.5 text-xs {group.counterparts.length
										? 'bg-surface-200-800'
										: 'bg-error-100-900 text-error-900-100'}"
								>
									{group.counterparts.length}
								</span>
							</td>
							<td class="px-3 py-2">
								{#if group.counterparts.length}
									<div class="flex flex-wrap gap-1">
										{#each group.counterparts as counterpart (counterpart.index)}
											<span
												class="rounded-sm px-2 py-0.5 text-xs {RELATIONSHIP_COLOR[
													counterpart.relationship ?? ''
												] ?? 'bg-surface-200-800'}"
												title={requirementLabel(counterpart)}
											>
												{refFor(counterpart.urn, counterpart.ref_id)}
											</span>
										{/each}
									</div>
								{:else}
									<span class="text-xs text-surface-500">{m.unmapped()}</span>
								{/if}
							</td>
						{/if}
					</tr>
				{:else}
					<tr>
						<td class="px-3 py-6 text-center text-surface-500" colspan={columns.length}>
							{m.noResults()}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	{#if pageCount > 1}
		<div class="flex flex-wrap items-center justify-between gap-2 text-sm">
			<select class="select w-28" bind:value={rowsPerPage} aria-label={m.rowsPerPage()}>
				{#each [25, 50, 100, 250] as size (size)}
					<option value={size}>{size}</option>
				{/each}
			</select>
			<div class="flex items-center gap-2">
				<button
					type="button"
					class="btn btn-sm preset-tonal"
					disabled={currentPage <= 1}
					onclick={() => (currentPage -= 1)}
				>
					{m.previous()}
				</button>
				<span class="text-surface-600-400">{currentPage} / {pageCount}</span>
				<button
					type="button"
					class="btn btn-sm preset-tonal"
					disabled={currentPage >= pageCount}
					onclick={() => (currentPage += 1)}
				>
					{m.next()}
				</button>
			</div>
		</div>
	{/if}
</div>
