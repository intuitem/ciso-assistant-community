<script lang="ts">
	import { run } from 'svelte/legacy';

	import type { RiskMatrixJsonDefinition } from '$lib/utils/types';
	import { formFieldProxy } from 'sveltekit-superforms';

	import { toCamelCase } from '$lib/utils/locales';
	import { safeTranslate } from '$lib/utils/i18n';
	import { isDark } from '$lib/utils/helpers';

	interface Props {
		label?: string | undefined;
		field: string;
		helpText?: string | undefined;
		riskMatrix: RiskMatrixJsonDefinition;
		probabilityField: string;
		impactField: string;
		form: any;
	}

	let {
		label = undefined,
		field,
		helpText = undefined,
		riskMatrix,
		probabilityField,
		impactField,
		form
	}: Props = $props();

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

	let riskLevel = $state(
		$probabilityValue >= 0 && $impactValue >= 0
			? riskMatrix.risk[gridPosition($probabilityValue, $impactValue)!]
			: undefined
	);

	run(() => {
		riskLevel =
			$probabilityValue >= 0 && $impactValue >= 0
				? riskMatrix.risk[gridPosition($probabilityValue, $impactValue)!]
				: undefined;
	});

	let classesCellText = $derived((backgroundHexColor: string) => {
		return isDark(backgroundHexColor) ? 'text-white' : '';
	});
</script>

<div class="flex flex-col">
	{#if label !== undefined}
		<label class="text-sm font-semibold" for={field}>{label}</label>
	{/if}
	{#if riskLevel}
		<div
			class="flex font-medium w-32 justify-center p-2 rounded-base {classesCellText(
				riskLevel.hexcolor
			)}"
			style="background-color: {riskLevel.hexcolor}"
		>
			{safeTranslate(riskLevel.name)}
		</div>
	{:else}
		<div class="flex font-medium w-32 justify-center p-2 rounded-base bg-gray-300">--</div>
	{/if}
	{#if helpText}
		<p class="text-sm text-gray-500 w-64">{helpText}</p>
	{/if}
</div>
