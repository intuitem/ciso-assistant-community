<script lang="ts">
	import { isDark } from '$lib/utils/helpers';
	import type { RiskMatrixJsonDefinition } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		parsedRiskMatrix: RiskMatrixJsonDefinition;
	}

	let { parsedRiskMatrix }: Props = $props();

	let classesCellText = $derived((backgroundHexColor: string | undefined | null): string => {
		if (!backgroundHexColor) return '';
		return isDark(backgroundHexColor) ? 'text-white' : 'text-surface-950';
	});
</script>

<div class="w-full flex flex-col justify-start mt-4">
	<h3 class="flex font-semibold pl-6 m-2 text-md">{m.riskLevels()}</h3>
	<div class="flex justify-start mx-2">
		<table class="w-auto border-separate" style="border-spacing: 0 6px;">
			<tbody>
				{#each parsedRiskMatrix.risk as riskItem}
					<tr>
						<td
							class="text-center px-3 py-1.5 font-semibold whitespace-nowrap rounded-md {classesCellText(
								riskItem.hexcolor
							)}"
							style="background-color: {riskItem.hexcolor}"
						>
							{riskItem.name}
						</td>
						<td class="italic pl-3 text-surface-700-300">
							{riskItem.description}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>
