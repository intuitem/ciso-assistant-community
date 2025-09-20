<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { m } from '$paraglide/messages';

	const EFFORT_REVERSE_MAP = { 1: 'XS', 2: 'S', 3: 'M', 4: 'L', 5: 'XL' };

	interface Props {
		data;
	}

	let { data }: Props = $props();

	let selectedCell: { impact: number; effort: number } | null = $state(null);
	let overrideFilters: { [key: string]: any[] } = $state({ control_impact: [], effort: [] });

	let modelTableKey = $state(0); // Force re-render when incremented

	function handleCellClick(rowIndex: number, colIndex: number) {
		const impact = 5 - rowIndex; // Convert grid position to impact value
		const effort = colIndex + 1; // Convert grid position to effort value
		const items = data[rowIndex][colIndex];

		selectedCell = { impact, effort };

		const effortLabel = EFFORT_REVERSE_MAP[effort];
		overrideFilters = {
			control_impact: [{ value: impact }],
			effort: [{ value: effortLabel }]
		};

		modelTableKey++; // Force ModelTable to refresh
	}

	function getCellStyle(rowIndex: number, colIndex: number) {
		const impact = 5 - rowIndex;
		const effort = colIndex + 1;

		if (impact >= 3 && effort <= 2) return 'bg-green-200 hover:bg-green-300';
		if (impact >= 3 && effort >= 3) return 'bg-yellow-200 hover:bg-yellow-300';
		if (impact <= 2 && effort >= 4) return 'bg-red-200 hover:bg-red-300';
		return 'bg-gray-100 hover:bg-gray-200';
	}

	function resetFilters() {
		selectedCell = null;
		overrideFilters = { control_impact: [], effort: [] };
		modelTableKey++;
	}
</script>

<main class="grid grid-cols-6">
	<div class="w-full max-w-screen-lg mx-auto p-4 col-span-4">
		<div class="grid grid-cols-6 gap-1 mb-6">
			<div class="flex justify-end items-center p-2 font-semibold">{m.pImpact()}</div>
			<div class="col-span-5"></div>

			<div class="flex justify-end items-center p-2 text-sm">5 ({m.high()})</div>
			<div class="col-span-5 row-span-5 border-2 border-gray-300 grid grid-cols-5 gap-1 p-1">
				{#each data as row, rowIndex}
					{#each row as col, colIndex}
						<button
							class="aspect-square flex flex-col items-center justify-center border border-gray-300 rounded text-xs p-1 transition-colors {getCellStyle(
								rowIndex,
								colIndex
							)} {selectedCell?.impact === 5 - rowIndex && selectedCell?.effort === colIndex + 1
								? 'ring-2 ring-blue-500'
								: ''}"
							onclick={() => handleCellClick(rowIndex, colIndex)}
						>
							{#if col.length > 0}
								<div class="font-semibold text-lg">{col.length}</div>
								<div class="text-xs text-gray-600">
									{#if col.length > 1}{m.items()}{:else}{m.item()}{/if}
								</div>
							{:else}
								<div class=""></div>
							{/if}
						</button>
					{/each}
				{/each}
			</div>

			<div class="flex justify-end items-center p-2 text-sm">4</div>
			<div class="flex justify-end items-center p-2 text-sm">3</div>
			<div class="flex justify-end items-center p-2 text-sm">2</div>
			<div class="flex justify-end items-center p-2 text-sm">1 ({m.low()})</div>

			<!-- Effort labels (bottom) -->
			<div class="flex justify-end items-center p-2 font-semibold">{m.effort()}</div>
			<div class="flex justify-center items-center p-2 text-sm">1 ({m.low()})</div>
			<div class="flex justify-center items-center p-2 text-sm">2</div>
			<div class="flex justify-center items-center p-2 text-sm">3</div>
			<div class="flex justify-center items-center p-2 text-sm">4</div>
			<div class="flex justify-center items-center p-2 text-sm">5 ({m.high()})</div>
		</div>
	</div>
	<!-- Legend -->
	<div class="mb-4 p-4 rounded">
		<h3 class="font-semibold mb-2">{m.priorityLegend()}</h3>
		<div class="flex flex-wrap gap-4 text-sm">
			<div class="flex items-center gap-2">
				<div class="w-4 h-4 bg-green-200 border"></div>
				<span>{m.quickWins()}</span>
			</div>
			<div class="flex items-center gap-2">
				<div class="w-4 h-4 bg-yellow-200 border"></div>
				<span>{m.majorProjects()}</span>
			</div>
			<div class="flex items-center gap-2">
				<div class="w-4 h-4 bg-gray-100 border"></div>
				<span>{m.fillIns()}</span>
			</div>
			<div class="flex items-center gap-2">
				<div class="w-4 h-4 bg-red-200 border"></div>
				<span>{m.questionable()}</span>
			</div>
		</div>
	</div>
</main>

<div class="px-4 text-xs text-slate-500">
	{m.impactEffortMatrixHint()}
</div>
<div class="rounded-lg border shadow-xl p-2 m-4">
	<div
		class="mb-4 p-2 {selectedCell
			? 'bg-blue-50 border-blue-200'
			: 'bg-gray-50 border-gray-200'} border rounded flex items-center justify-between"
	>
		<span class="text-sm {selectedCell ? 'text-blue-800' : 'text-gray-600'}">
			{#if selectedCell}
				{m.showingItemsWith()}
				{m.controlImpact()}: {selectedCell.impact}, {m.effort()}: {selectedCell.effort}
			{:else}
				{m.showingAllAppliedControls()}
			{/if}
		</span>
		<button
			class="px-3 py-1 text-sm {selectedCell
				? 'bg-blue-600 hover:bg-blue-700'
				: 'bg-gray-400 cursor-not-allowed'} text-white rounded transition-colors"
			onclick={() => resetFilters()}
			disabled={!selectedCell}
		>
			{selectedCell ? m.resetFilter() : m.noActiveFilter()}
		</button>
	</div>
	{#key modelTableKey}
		<ModelTable
			source={{
				head: {
					ref_id: 'ref_id',
					name: 'name',
					status: 'status',
					priority: 'priority',
					eta: 'eta',
					folder: 'folder',
					effort: 'effort',
					control_impact: 'control_impact'
				},
				body: []
			}}
			{overrideFilters}
			hideFilters={true}
			URLModel="applied-controls"
		/>
	{/key}
</div>
<div class="h-4"></div>
