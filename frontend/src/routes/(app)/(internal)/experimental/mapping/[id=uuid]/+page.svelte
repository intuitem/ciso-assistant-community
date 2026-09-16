<script lang="ts">
	import type { PageData } from './$types';
	import GraphExplorer from '$lib/components/DataViz/GraphExplorer.svelte';
	import MappingTable from '$lib/components/Mapping/MappingTable.svelte';
	import SegmentedControl from '$lib/components/Forms/SegmentedControl.svelte';
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Derived, not destructured: navigating between mapping sets reuses this
	// component, so captured values would describe the previous set.
	const meta = $derived(data.data.meta);

	$effect(() => pageTitle.set(meta.display_name));

	let view: 'graph' | 'table' = $state('graph');

	const viewOptions = [
		{ value: 'graph', label: m.graph() },
		{ value: 'table', label: m.table() }
	];
</script>

<div class="bg-surface-50-950 shadow-sm flex flex-col overflow-x-auto">
	<div class="px-4 py-2 border-b border-surface-200-800 flex items-start justify-between gap-4">
		<div class="flex flex-col gap-1 text-sm">
			<div>
				<span class="text-surface-600-400">{meta.source_framework} → {meta.target_framework}:</span>
				<span class="font-semibold">{meta.target_coverage ?? 0}%</span>
				<span class="text-surface-400-600">({meta.target_linked}/{meta.target_total})</span>
			</div>
			<div>
				<span class="text-surface-600-400">{meta.target_framework} → {meta.source_framework}:</span>
				<span class="font-semibold">{meta.source_coverage ?? 0}%</span>
				<span class="text-surface-400-600">({meta.source_linked}/{meta.source_total})</span>
			</div>
		</div>
		<SegmentedControl
			options={viewOptions}
			value={view}
			onChange={(value) => (view = value as 'graph' | 'table')}
			size="sm"
			ariaLabel={m.viewMode()}
		/>
	</div>
	{#if view === 'graph'}
		<div class="w-full h-screen">
			<GraphExplorer title="Mapping Explorer" data={data.data} />
		</div>
	{:else}
		{#await data.tableData}
			<span class="p-4 text-sm text-surface-600-400" data-testid="loading-field">
				{m.loading()}...
			</span>
		{:then tableData}
			<MappingTable
				rows={tableData.rows}
				sourceRequirements={tableData.source_requirements}
				targetRequirements={tableData.target_requirements}
				sourceFramework={meta.source_framework}
				targetFramework={meta.target_framework}
			/>
		{/await}
	{/if}
</div>
