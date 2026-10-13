<script lang="ts">
	import { page } from '$app/state';
	import { isDark } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';

	interface Level {
		id: number;
		abbreviation: string;
		name: string;
		description: string;
		hexcolor: string;
		translations?: Record<string, { name?: string; description?: string }>;
	}

	interface Props {
		grid: number[][];
		probabilityLevels: Level[];
		impactLevels: Level[];
		riskLevels: Level[];
		onchange: (grid: number[][]) => void;
		/** When editing a translation, display level names in that language. */
		activeLang?: string;
		baseLang?: string;
		// Axis configuration, mirroring the RiskMatrix preview component.
		swapAxes?: boolean;
		flipVertical?: boolean;
		labelStandard?: string;
	}

	let {
		grid = $bindable(),
		probabilityLevels,
		impactLevels,
		riskLevels,
		onchange,
		activeLang,
		baseLang,
		swapAxes = page.data.settings?.risk_matrix_swap_axes ?? false,
		flipVertical = page.data.settings?.risk_matrix_flip_vertical ?? false,
		labelStandard = page.data.settings?.risk_matrix_labels ?? 'ISO'
	}: Props = $props();

	// Translated display name with base-language fallback (abbreviations are
	// not translated — the levels' translations carry name/description only).
	function levelName(level: Level): string {
		if (activeLang && activeLang !== baseLang) {
			return level.translations?.[activeLang]?.name || level.name;
		}
		return level.name;
	}

	// The stored grid stays grid[probabilityIndex][impactIndex]; only the
	// rendering is reoriented.
	function toGridCoords(yIdx: number, xIdx: number): [number, number] {
		return swapAxes ? [xIdx, yIdx] : [yIdx, xIdx];
	}

	function cycleRiskLevel(yIdx: number, xIdx: number) {
		const [rowIdx, colIdx] = toGridCoords(yIdx, xIdx);
		setRiskLevel(yIdx, xIdx, ((grid[rowIdx]?.[colIdx] ?? 0) + 1) % riskLevels.length);
	}

	function setRiskLevel(yIdx: number, xIdx: number, value: number) {
		const [rowIdx, colIdx] = toGridCoords(yIdx, xIdx);
		grid = grid.map((row, ri) =>
			ri === rowIdx ? row.map((cell, ci) => (ci === colIdx ? value : cell)) : row
		);
		onchange(grid);
	}

	function getRiskLevel(yIdx: number, xIdx: number): Level | undefined {
		const [rowIdx, colIdx] = toGridCoords(yIdx, xIdx);
		return riskLevels[grid[rowIdx]?.[colIdx] ?? 0];
	}

	let yLevels = $derived(swapAxes ? impactLevels : probabilityLevels);
	let xLevels = $derived(swapAxes ? probabilityLevels : impactLevels);

	let yAxisLabel = $derived(
		safeTranslate(`${swapAxes ? 'impact' : 'probability'}${labelStandard}`)
	);
	let xAxisLabel = $derived(
		safeTranslate(`${swapAxes ? 'probability' : 'impact'}${labelStandard}`)
	);

	// Highest level at the top, unless the origin is set to top-left.
	let displayRows = $derived.by(() => {
		const rows = yLevels.map((level, yIdx) => ({ level, yIdx }));
		return flipVertical ? rows : rows.reverse();
	});
</script>

<div class="space-y-3">
	<div class="flex items-center">
		<div class="flex font-semibold text-sm text-surface-600-400 -rotate-90 whitespace-nowrap mr-1">
			<!-- -rotate-90 turns → upward and ← downward; the arrow follows increasing level order. -->
			{flipVertical ? `← ${yAxisLabel}` : `${yAxisLabel} →`}
		</div>
		<div class="overflow-x-auto flex-1">
			<table class="table table-compact border-collapse">
				<thead>
					<tr>
						<th class="bg-surface-100-900 border border-surface-300-700 text-center w-28"></th>
						{#each xLevels as xLevel}
							<th
								class="border border-surface-300-700 text-center p-2 min-w-20"
								style="background-color: {xLevel.hexcolor}; color: {isDark(xLevel.hexcolor)
									? 'white'
									: 'black'}"
							>
								<span class="text-xs font-bold">{xLevel.abbreviation}</span>
								<br />
								<span class="text-xs">{levelName(xLevel)}</span>
							</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each displayRows as { level, yIdx }, displayIdx}
						{@const isBottomHalf = displayIdx >= displayRows.length / 2}
						<tr>
							<td
								class="border border-surface-300-700 text-center p-2 font-semibold"
								style="background-color: {level.hexcolor}; color: {isDark(level.hexcolor)
									? 'white'
									: 'black'}"
							>
								<span class="text-xs font-bold">{level.abbreviation}</span>
								<br />
								<span class="text-xs">{levelName(level)}</span>
							</td>
							{#each xLevels as _, xIdx}
								{@const riskLevel = getRiskLevel(yIdx, xIdx)}
								<td
									class="border border-surface-300-700 text-center p-0 cursor-pointer hover:opacity-80 transition-opacity focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-1"
									style="background-color: {riskLevel?.hexcolor ?? '#ccc'}; color: {isDark(
										riskLevel?.hexcolor ?? '#ccc'
									)
										? 'white'
										: 'black'}"
									onclick={() => cycleRiskLevel(yIdx, xIdx)}
									title={m.clickToCycle()}
									role="button"
									tabindex="0"
									onkeydown={(e) => {
										if (e.key === 'Enter' || e.key === ' ') {
											e.preventDefault();
											cycleRiskLevel(yIdx, xIdx);
										}
									}}
								>
									<div class="relative group">
										<span class="text-sm font-bold py-3 px-4 block">
											{riskLevel?.abbreviation ?? '?'}
										</span>
										<!-- Dropdown on hover (flips upward for bottom rows) -->
										<div
											class="hidden group-hover:block absolute left-0 z-10 bg-surface-50-950 shadow-lg rounded border min-w-24 {isBottomHalf
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
														setRiskLevel(yIdx, xIdx, rIdx);
													}}
												>
													{rl.abbreviation} - {levelName(rl)}
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
	<div class="flex justify-center text-sm font-semibold text-surface-600-400 mt-1">
		{xAxisLabel} →
	</div>
	<p class="text-xs text-surface-500 text-center mt-2">
		<i class="fa-solid fa-circle-info mr-1"></i>{m.clickToCycle()}
	</p>
</div>
