<script lang="ts">
	import type { RiskMatrixJsonDefinition } from '$lib/utils/types';
	import { formFieldProxy } from 'sveltekit-superforms';

	import { localItems, toCamelCase } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';

	export let label: string | undefined = undefined;
	export let field: string;
	export let helpText: string | undefined = undefined;

	export let riskMatrix: RiskMatrixJsonDefinition;

	export let probabilityField: string;
	export let impactField: string;

	export let form;

	const { value: probabilityValue } = formFieldProxy(form, probabilityField);
	const { value: impactValue } = formFieldProxy(form, impactField);

	const gridPosition = (probabilityValue: number, impactValue: number) => {
		if (
			probabilityValue === undefined ||
			impactValue === undefined ||
			probabilityValue < 0 ||
			probabilityValue > riskMatrix.grid.length ||
			impactValue < 0 ||
			impactValue > riskMatrix.grid[0].length
		) {
			return undefined;
		}

		return riskMatrix.grid[probabilityValue][impactValue];
	};

	let riskLevel =
		$probabilityValue >= 0 && $impactValue >= 0
			? riskMatrix.risk[gridPosition($probabilityValue, $impactValue)!]
			: undefined;

	$: riskLevel =
		$probabilityValue >= 0 && $impactValue >= 0
			? riskMatrix.risk[gridPosition($probabilityValue, $impactValue)!]
			: undefined;
</script>

<div class="flex flex-col">
	{#if label !== undefined}
		<label class="text-sm font-semibold" for={field}>{label}</label>
	{/if}
	{#if riskLevel}
		<div
			class="flex font-medium w-32 justify-center p-2 rounded-token"
			style="background-color: {riskLevel.hexcolor}"
		>
			{#if m[toCamelCase(riskLevel.name)]()}
				{m[toCamelCase(riskLevel.name)]() ?? riskLevel.name}
			{:else}
				{riskLevel.name}
			{/if}
		</div>
	{:else}
		<div class="flex font-medium w-32 justify-center p-2 rounded-token bg-gray-300">--</div>
	{/if}
	{#if helpText}
		<p class="text-sm text-gray-500 w-64">{helpText}</p>
	{/if}
</div>
