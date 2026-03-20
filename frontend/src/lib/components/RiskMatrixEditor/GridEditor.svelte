<script lang="ts">
	import { isDark } from '$lib/utils/helpers';
	import { m } from '$paraglide/messages';

	interface Level {
		id: number;
		abbreviation: string;
		name: string;
		description: string;
		hexcolor: string;
	}

	interface Props {
		grid: number[][];
		probabilityLevels: Level[];
		impactLevels: Level[];
		riskLevels: Level[];
		onchange: (grid: number[][]) => void;
	}

	let {
		grid = $bindable(),
		probabilityLevels,
		impactLevels,
		riskLevels,
		onchange
	}: Props = $props();

	function cycleRiskLevel(rowIdx: number, colIdx: number) {
		const current = grid[rowIdx][colIdx];
		const next = (current + 1) % riskLevels.length;
		grid = grid.map((row, ri) =>
			ri === rowIdx ? row.map((cell, ci) => (ci === colIdx ? next : cell)) : row
		);
		onchange(grid);
	}

	function setRiskLevel(rowIdx: number, colIdx: number, value: number) {
		grid = grid.map((row, ri) =>
			ri === rowIdx ? row.map((cell, ci) => (ci === colIdx ? value : cell)) : row
		);
		onchange(grid);
	}

	function getRiskLevel(index: number): Level | undefined {
		return riskLevels[index];
	}

	// Display probability rows reversed (highest at top) to match the preview component
	let displayRows = $derived(
		probabilityLevels
			.map((prob, idx) => ({ prob, gridRowIdx: idx }))
			.slice()
			.reverse()
	);
</script>

<div class="space-y-3">
	<div class="flex items-center">
		<div class="flex font-semibold text-sm text-gray-500 -rotate-90 whitespace-nowrap mr-1">
			← {m.probability()}
		</div>
		<div class="overflow-x-auto flex-1">
			<table class="table table-compact border-collapse">
				<thead>
					<tr>
						<th class="bg-gray-100 border border-gray-300 text-center w-28"></th>
						{#each impactLevels as impact}
							<th
								class="border border-gray-300 text-center p-2 min-w-20"
								style="background-color: {impact.hexcolor}; color: {isDark(impact.hexcolor)
									? 'white'
									: 'black'}"
							>
								<span class="text-xs font-bold">{impact.abbreviation}</span>
								<br />
								<span class="text-xs">{impact.name}</span>
							</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each displayRows as { prob, gridRowIdx }, displayIdx}
						{@const rowIdx = gridRowIdx}
						{@const isBottomHalf = displayIdx >= displayRows.length / 2}
						<tr>
							<td
								class="border border-gray-300 text-center p-2 font-semibold"
								style="background-color: {prob.hexcolor}; color: {isDark(prob.hexcolor)
									? 'white'
									: 'black'}"
							>
								<span class="text-xs font-bold">{prob.abbreviation}</span>
								<br />
								<span class="text-xs">{prob.name}</span>
							</td>
							{#each impactLevels as _, colIdx}
								{@const riskLevel = getRiskLevel(grid[rowIdx]?.[colIdx] ?? 0)}
								<td
									class="border border-gray-300 text-center p-0 cursor-pointer hover:opacity-80 transition-opacity"
									style="background-color: {riskLevel?.hexcolor ?? '#ccc'}; color: {isDark(
										riskLevel?.hexcolor ?? '#ccc'
									)
										? 'white'
										: 'black'}"
									onclick={() => cycleRiskLevel(rowIdx, colIdx)}
									title="Click to cycle, or right-click for dropdown"
									role="button"
									tabindex="0"
									onkeydown={(e) => {
										if (e.key === 'Enter' || e.key === ' ') {
											e.preventDefault();
											cycleRiskLevel(rowIdx, colIdx);
										}
									}}
								>
									<div class="relative group">
										<span class="text-sm font-bold p-2 block">
											{riskLevel?.abbreviation ?? '?'}
										</span>
										<!-- Dropdown on hover (flips upward for bottom rows) -->
										<div
											class="hidden group-hover:block absolute left-0 z-10 bg-white shadow-lg rounded border min-w-24 {isBottomHalf
												? 'bottom-full'
												: 'top-full'}"
										>
											{#each riskLevels as rl, rIdx}
												<button
													type="button"
													class="block w-full text-left px-2 py-1 text-xs hover:opacity-80"
													style="background-color: {rl.hexcolor}; color: {isDark(rl.hexcolor)
														? 'white'
														: 'black'}"
													onclick={(e) => {
														e.stopPropagation();
														setRiskLevel(rowIdx, colIdx, rIdx);
													}}
												>
													{rl.abbreviation} - {rl.name}
												</button>
											{/each}
										</div>
									</div>
								</td>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>
	<div class="flex justify-center text-sm font-semibold text-gray-500 mt-1">
		{m.impact()} →
	</div>
</div>
