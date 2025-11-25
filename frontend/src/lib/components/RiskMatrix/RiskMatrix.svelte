<script lang="ts">
	import { Tooltip } from '@skeletonlabs/skeleton-svelte';
	import Cell from './Cell.svelte';
	import { buildRiskMatrix, reverseRows, transpose } from './utils';

	import { page } from '$app/state';
	import { isDark } from '$lib/utils/helpers';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { ComponentType } from 'svelte';
	import Legend from './Legend.svelte';

	interface Props {
		// --- Props ---
		riskMatrix: any;
		wrapperClass?: string | undefined;
		matrixName: string; // used to differentiate bubbles tooltip names
		showLegend?: boolean;
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
		showLegend: showRisks = false,
		useBubbles = false,
		data = undefined,
		dataItemComponent = undefined,
		swapAxes = page.data.settings.risk_matrix_swap_axes ?? false,
		flipVertical = page.data.settings.risk_matrix_flip_vertical ?? false,
		labelStandard = page.data.settings.risk_matrix_labels ?? 'ISO'
	}: Props = $props();

	const parsedRiskMatrix = JSON.parse(riskMatrix.json_definition);
	const grid = parsedRiskMatrix.grid;
	const risk = parsedRiskMatrix.risk;
	const originalProbabilities = parsedRiskMatrix.probability;
	const originalImpacts = parsedRiskMatrix.impact;

	let finalMatrix: ReturnType<typeof buildRiskMatrix> = $state();
	let finalData: typeof data | undefined = $state();

	// Headers assignment remains the same
	let rawYAxisHeaders = $derived(swapAxes ? originalImpacts : originalProbabilities);
	let yAxisHeaders: typeof rawYAxisHeaders = $state([]);
	let xAxisHeaders = $derived(swapAxes ? originalProbabilities : originalImpacts);

	let popupHoverY = $derived(
		yAxisHeaders.map((_, i) => ({
			event: 'hover',
			target: `popup-${matrixName}-y-${i}`,
			placement: swapAxes ? 'right' : 'bottom'
		}))
	);
	let popupHoverX = $derived(
		xAxisHeaders.map((_, i) => ({
			event: 'hover',
			target: `popup-${matrixName}-x-${i}`,
			placement: 'bottom'
		}))
	);

	let yAxisType = $derived(swapAxes ? 'impact' : 'probability');
	let xAxisType = $derived(swapAxes ? 'probability' : 'impact');

	let yAxisLabel = $derived(safeTranslate(`${yAxisType}${labelStandard}`));
	let xAxisLabel = $derived(safeTranslate(`${xAxisType}${labelStandard}`));

	let baseMatrix = $derived(buildRiskMatrix(grid, risk));

	let baseData = $derived(
		data ? (data.some((row) => row && row.length > 0) ? data : undefined) : undefined
	);

	$effect(() => {
		yAxisHeaders = flipVertical ? rawYAxisHeaders.slice().reverse() : rawYAxisHeaders;

		let matrix = baseMatrix;
		let transformedData = baseData ? reverseRows(baseData) : undefined;

		if (swapAxes) {
			matrix = transpose(matrix);
			transformedData = transformedData && transpose(transformedData);
		}

		if (flipVertical) {
			matrix = reverseRows(matrix);
			transformedData = transformedData && reverseRows(transformedData);
		}

		finalMatrix = matrix;
		finalData = transformedData ?? [];
	});

	let classesCellText = $derived((backgroundHexColor: string | undefined | null): string => {
		if (!backgroundHexColor) return '';
		return isDark(backgroundHexColor) ? 'text-white' : 'text-black';
	});
</script>

<!-- should go Component? -->
{#snippet xAxisHeadersSnippet()}
	{#each xAxisHeaders as xHeader, j}
		<div
			class="flex flex-col items-center justify-center bg-gray-200 min-h-20 border-dotted border-black border-2 text-center p-1 {classesCellText(
				xHeader.hexcolor
			)}"
			style="background: {xHeader.hexcolor ?? '#FFFFFF'}"
			data-testid="x-axis-header-{j}"
		>
			<Tooltip
				open={popupHoverX[j].open}
				onOpenChange={(e) => (popupHoverX[j].open = e.open)}
				openDelay={0}
				closeDelay={100}
			>
				{#snippet content()}
					<div
						class="card bg-black p-4 z-20 shadow-lg rounded-sm max-w-xl"
						style="color: {xHeader.hexcolor ?? '#FFFFFF'}"
					>
						<p data-testid="x-header-description" class="font-semibold">
							{xHeader.description}
						</p>
						<div class="arrow bg-black"></div>
					</div>
				{/snippet}
				{#snippet trigger()}
					<span class="font-semibold p-1" data-testid="x-header-name">{xHeader.name}</span>
					{#if xHeader.description}
						<i class="fa-solid fa-circle-info cursor-help *:pointer-events-none mt-1"></i>
					{/if}
				{/snippet}
			</Tooltip>
		</div>
	{/each}
{/snippet}

<div class="flex flex-row items-center">
	<div
		class="flex font-semibold text-xl -rotate-90 whitespace-nowrap mx-auto"
		data-testid="y-label"
	>
		{yAxisLabel}
	</div>

	<div class="flex flex-col w-full">
		{#if flipVertical}
			<div
				class="flex font-semibold text-xl items-center justify-center p-2 mt-1"
				data-testid="x-label-flipped"
			>
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
				{@render xAxisHeadersSnippet()}
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
					<Tooltip
						open={popupHoverY[i].open}
						onOpenChange={(e) => (popupHoverY[i].open = e.open)}
						openDelay={0}
						closeDelay={100}
						positioning={{ placement: 'bottom-end' }}
					>
						{#snippet content()}
							<div
								class="card bg-black p-4 z-20 shadow-lg rounded-sm max-w-xl"
								style="color: {yHeader.hexcolor ?? '#FFFFFF'}"
							>
								<p data-testid="y-header-description" class="font-semibold">
									{yHeader.description}
								</p>
								<div class="arrow bg-black"></div>
							</div>
						{/snippet}
						{#snippet trigger()}
							<span class="font-semibold p-1" data-testid="y-header-name">{yHeader.name}</span>
							{#if yHeader.description}
								<i class="fa-solid fa-circle-info cursor-help *:pointer-events-none mt-1"></i>
							{/if}
						{/snippet}
					</Tooltip>
				</div>

				{#each row as cell, j}
					<Cell
						{cell}
						cellData={finalData ? finalData[i]?.[j] : undefined}
						{dataItemComponent}
						{useBubbles}
					/>
				{/each}
			{/each}

			{#if !flipVertical}
				<div></div>
				{@render xAxisHeadersSnippet()}
			{/if}
		</div>
		{#if !flipVertical}
			<div
				class="flex font-semibold text-xl items-center justify-center p-2 mt-1"
				data-testid="x-label"
			>
				{xAxisLabel}
			</div>
		{/if}
	</div>
</div>

{#if showRisks}
	<Legend {parsedRiskMatrix} />
{/if}
