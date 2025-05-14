<script lang="ts">
	import { run } from 'svelte/legacy';

	import Cell from './Cell.svelte';
	import { buildRiskMatrix, reverseCols, reverseRows, transpose } from './utils';

	import { page } from '$app/state';
	import { isDark } from '$lib/utils/helpers';
	import { m } from '$paraglide/messages';
	import { type PopupSettings } from '@skeletonlabs/skeleton-svelte';
	import type { ComponentType } from 'svelte';
	import { safeTranslate } from '$lib/utils/i18n';

	

	
	interface Props {
		// --- Props ---
		riskMatrix: any;
		wrapperClass?: string | undefined;
		matrixName: string; // used to differentiate bubbles tooltip names
		showRisks?: boolean;
		useBubbles?: boolean;
		data?: Array<Array<any>> | undefined; // Ensure data is typed correctly
		dataItemComponent?: ComponentType | undefined;
		// Axis configuration props
		swapAxes?: boolean; // Probability on X, Impact on Y if true
		flipVertical?: boolean; // Origin top-left for Y-axis if true
		labelStandard?: string;
	}

	let {
		riskMatrix,
		wrapperClass = '',
		matrixName,
		showRisks = false,
		useBubbles = false,
		data = undefined,
		dataItemComponent = undefined,
		swapAxes = page.data.settings.risk_matrix_swap_axes ?? false,
		flipVertical = page.data.settings.risk_matrix_flip_vertical ?? false,
		labelStandard = page.data.settings.risk_matrix_labels ?? 'ISO'
	}: Props = $props();

	run(() => {
		console.log(page.data.settings);
	});

	const parsedRiskMatrix = JSON.parse(riskMatrix.json_definition);
	const grid = parsedRiskMatrix.grid;
	const risk = parsedRiskMatrix.risk;
	const originalProbabilities = parsedRiskMatrix.probability;
	const originalImpacts = parsedRiskMatrix.impact;

	let yAxisLabel: string = $state();
	let xAxisLabel: string = $state();
	let yAxisHeaders: typeof originalProbabilities | typeof originalImpacts = $state();
	let xAxisHeaders: typeof originalImpacts | typeof originalProbabilities = $state();
	let finalMatrix: ReturnType<typeof buildRiskMatrix> = $state();
	let finalData: typeof data | undefined = $state();
	let popupHoverY: PopupSettings[] = $state([]);
	let popupHoverX: PopupSettings[] = $state([]);

	run(() => {
		// Determine base axis types
		const yAxisType = swapAxes ? 'impact' : 'probability';
		const xAxisType = swapAxes ? 'probability' : 'impact';

		// Generate the full translation keys with the standard
		yAxisLabel = safeTranslate(`${yAxisType}${labelStandard}`);
		xAxisLabel = safeTranslate(`${xAxisType}${labelStandard}`);

		// Headers assignment remains the same
		yAxisHeaders = swapAxes ? originalImpacts : originalProbabilities;
		xAxisHeaders = swapAxes ? originalProbabilities : originalImpacts;

		// Build the initial matrix (always built as prob (Y) vs impact (X))
		let baseMatrix = buildRiskMatrix(grid, risk);
		let baseData = data
			? data.some((row) => row && row.length > 0)
				? data
				: undefined
			: undefined;

		// Swap axes if needed
		if (swapAxes) {
			baseMatrix = transpose(baseMatrix);
			if (baseData) {
				baseData = transpose(baseData);
			}
		}

		// Flip vertically if needed
		if (flipVertical) {
			yAxisHeaders = yAxisHeaders.slice().reverse();
			baseMatrix = reverseRows(baseMatrix);
			if (baseData) {
				baseData = reverseRows(baseData);
			}
		}

		// Assign final derived values
		finalMatrix = baseMatrix;
		finalData = baseData ? (swapAxes ? reverseCols(baseData) : reverseRows(baseData)) : []; // Ensure data is in the correct orientation

		// Recalculate popup settings based on final headers
		popupHoverY = yAxisHeaders.map((_, i) => ({
			event: 'hover',
			target: `popup-${matrixName}-y-${i}`,
			placement: swapAxes ? 'right' : 'bottom' // Adjust placement based on orientation
		}));

		popupHoverX = xAxisHeaders.map((_, i) => ({
			event: 'hover',
			target: `popup-${matrixName}-x-${i}`,
			placement: 'bottom'
		}));
	});

	let classesCellText = $derived((backgroundHexColor: string | undefined | null): string => {
		if (!backgroundHexColor) return '';
		return isDark(backgroundHexColor) ? 'text-white' : 'text-black';
	});
</script>

<div class="flex flex-row items-center">
	<div class="flex font-semibold text-xl -rotate-90 whitespace-nowrap mx-auto">
		{yAxisLabel}
	</div>

	<div class="flex flex-col w-full">
		{#if flipVertical}
			<div class="flex font-semibold text-xl items-center justify-center p-2 mt-1">
				{xAxisLabel}
			</div>
		{/if}
		<div
			class="{wrapperClass} grid gap-1 w-full"
			style="grid-template-columns: auto repeat({xAxisHeaders.length}, minmax(0, 1fr)); grid-template-rows: repeat({yAxisHeaders.length}, minmax(0, 1fr)) auto;"
			data-testid="risk-matrix"
		>
			{#if flipVertical}
				<div></div>

				{#each xAxisHeaders as xHeader, j}
					<div
						class="flex flex-col items-center justify-center bg-gray-200 min-h-20 border-dotted border-black border-2 text-center p-1 {classesCellText(
							xHeader.hexcolor
						)}"
						style="background: {xHeader.hexcolor ?? '#FFFFFF'}"
						data-testid="x-axis-header-{j}"
					>
						<div
							class="card bg-black text-gray-200 p-4 z-20 shadow-lg rounded-sm"
							style="color: {xHeader.hexcolor ?? '#FFFFFF'}"
							data-popup={'popup-' + matrixName + '-x-' + j}
						>
							<p data-testid="x-header-description" class="font-semibold">{xHeader.description}</p>
							<div class="arrow bg-black"></div>
						</div>
						<span class="font-semibold p-1" data-testid="x-header-name">{xHeader.name}</span>
						{#if xHeader.description}
							<i
								class="fa-solid fa-circle-info cursor-help *:pointer-events-none mt-1"
								use:popup={popupHoverX[j]}
							></i>
						{/if}
					</div>
				{/each}
			{/if}
			{#each finalMatrix as row, i}
				{@const yHeader = yAxisHeaders[finalMatrix.length - 1 - i]}
				<div
					class="flex flex-col items-center min-h-20 justify-center bg-gray-200 border-dotted border-black border-2 text-center p-1 {classesCellText(
						yHeader.hexcolor
					)}"
					style="background: {yHeader.hexcolor ?? '#FFFFFF'}"
					data-testid="y-axis-header-{i}"
				>
					<div
						class="card bg-black text-gray-200 p-4 z-20 shadow-lg rounded-sm"
						style="color: {yHeader.hexcolor ?? '#FFFFFF'}"
						data-popup={'popup-' + matrixName + '-y-' + i}
					>
						<p data-testid="y-header-description" class="font-semibold">
							{yHeader.description}
						</p>
						<div class="arrow bg-black"></div>
					</div>
					<span class="font-semibold p-1" data-testid="y-header-name">{yHeader.name}</span>
					{#if yHeader.description}
						<i
							class="fa-solid fa-circle-info cursor-help *:pointer-events-none mt-1"
							use:popup={popupHoverY[i]}
						></i>
					{/if}
				</div>

				{#each row as cell, j}
					<Cell
						{cell}
						cellData={finalData ? finalData[i]?.[j] : undefined}
						popupTarget={`popupdata-${matrixName}-${i}-${j}`}
						{dataItemComponent}
						{useBubbles}
					/>
				{/each}
			{/each}

			{#if !flipVertical}
				<div></div>

				{#each xAxisHeaders as xHeader, j}
					<div
						class="flex flex-col items-center justify-center bg-gray-200 min-h-20 border-dotted border-black border-2 text-center p-1 {classesCellText(
							xHeader.hexcolor
						)}"
						style="background: {xHeader.hexcolor ?? '#FFFFFF'}"
						data-testid="x-axis-header-{j}"
					>
						<div
							class="card bg-black text-gray-200 p-4 z-20 shadow-lg rounded-sm"
							style="color: {xHeader.hexcolor ?? '#FFFFFF'}"
							data-popup={'popup-' + matrixName + '-x-' + j}
						>
							<p data-testid="x-header-description" class="font-semibold">{xHeader.description}</p>
							<div class="arrow bg-black"></div>
						</div>
						<span class="font-semibold p-1" data-testid="x-header-name">{xHeader.name}</span>
						{#if xHeader.description}
							<i
								class="fa-solid fa-circle-info cursor-help *:pointer-events-none mt-1"
								use:popup={popupHoverX[j]}
							></i>
						{/if}
					</div>
				{/each}
			{/if}
		</div>
		{#if !flipVertical}
			<div class="flex font-semibold text-xl items-center justify-center p-2 mt-1">
				{xAxisLabel}
			</div>
		{/if}
	</div>
</div>

{#if showRisks}
	<div class="w-full flex flex-col justify-start mt-4">
		<h3 class="flex font-semibold p-2 m-2 text-md">{m.riskLevels()}</h3>
		<div class="flex justify-start mx-2">
			<table class="w-auto border-separate" style="border-spacing: 0 4px;">
				<thead>
					<tr>
						<th class="text-left pb-2 px-2 font-semibold">{m.level()}</th>
						<th class="text-left pb-2 px-2 font-semibold">{m.description()}</th>
					</tr>
				</thead>
				<tbody>
					{#each parsedRiskMatrix.risk as riskItem}
						<tr class="col">
							<td
								class="w-auto text-center border-4 border-white p-2 font-semibold whitespace-nowrap rounded-l {classesCellText(
									riskItem.hexcolor
								)}"
								style="background-color: {riskItem.hexcolor}"
							>
								{riskItem.name}
							</td>
							<td class="col italic pl-3 border-t-4 border-b-4 border-r-4 border-white rounded-r">
								{riskItem.description}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>
{/if}
