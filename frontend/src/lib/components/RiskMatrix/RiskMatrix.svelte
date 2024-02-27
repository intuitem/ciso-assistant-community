<script lang="ts">
	import { buildRiskMatrix } from './utils';

	import * as m from '../../../paraglide/messages';
	import type { ComponentType } from 'svelte';

	export let riskMatrix;
	export let wrapperClass: string | undefined = '';

	const parsedRiskMatrix = JSON.parse(riskMatrix.json_definition);
	const grid = parsedRiskMatrix.grid;
	const risk = parsedRiskMatrix.risk;
	export let showRisks = false;

	const displayedRiskMatrix = buildRiskMatrix(grid, risk);
	export let data: Array<any> | undefined = undefined;
	export let dataItemComponent: ComponentType | undefined = undefined;
	// reverse data array to display it in the right order
	let displayedData: typeof data;
	if (data) {
		displayedData = data.some((e) => {
			return e.length;
		})
			? data.slice().reverse()
			: undefined;
	}
</script>

<div class="flex flex-row items-center">
	<div class="flex font-semibold text-xl -rotate-90">{m.probability()}</div>
	<div
		class="{wrapperClass} grid gap-1 w-full"
		style="grid-template-columns: repeat({displayedRiskMatrix.length + 1}, minmax(0, 1fr));"
		data-testid="risk-matrix"
	>
		{#each displayedRiskMatrix as row, i}
			{@const reverseIndex = displayedRiskMatrix.length - i - 1}
			{@const probability = parsedRiskMatrix.probability[reverseIndex]}
			<div
				class="flex flex-col items-center justify-center bg-gray-200"
				data-testid="probability-row-header"
			>
				<span class="font-semibold text-center" data-testid="probability-name"
					>{probability.name}</span
				>
				<span class="text-xs text-center" data-testid="probability-description"
					>{probability.description}</span
				>
			</div>
			{#each row as cell, j}
				<div
					class="flex flex-wrap items-center space-x-1 justify-center h-20 [&>*]:pointer-events-none whitespace-normal overflow-y-scroll hide-scrollbar"
					style="background-color: {cell.level.hexcolor};"
					data-testid="cell"
				>
					{#if displayedData}
						{#if dataItemComponent}
							{#each displayedData[i][j] as item}
								<svelte:component this={dataItemComponent} data={item} />
							{/each}
						{:else}
							<div class="mx-auto text-center">{displayedData[i][j]}</div>
						{/if}
					{/if}
				</div>
			{/each}
		{/each}
		<div />
		{#each parsedRiskMatrix.impact as impact}
			<div
				class="flex flex-col items-center justify-center bg-gray-200 h-20"
				data-testid="impact-col-header"
			>
				<span class="font-semibold" data-testid="impact-name">{impact.name}</span>
				<span class="text-xs" data-testid="impact-description">{impact.description}</span>
			</div>
		{/each}
	</div>
</div>
<div class="flex font-semibold text-xl items-center justify-center p-2 pl-60">{m.impact()}</div>
{#if showRisks}
	<div class="w-full flex flex-col justify-start">
		<h3 class="flex font-semibold p-2 m-2 text-md">{m.riskLevels()}</h3>
		<div class="flex justify-start mx-2">
			<table class="w-3/4 border-separate">
				{#each parsedRiskMatrix.risk as risk}
					<tr class="col">
						<td
							class="w-16 text-center border-4 border-white p-2 font-semibold whitespace-nowrap"
							style="background-color: {risk.hexcolor}"
						>
							{risk.name}
						</td>
						<td class="col italic">
							{risk.description}
						</td>
					</tr>
				{/each}
			</table>
		</div>
	</div>
{/if}
