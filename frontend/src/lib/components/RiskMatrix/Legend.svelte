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
		return isDark(backgroundHexColor) ? 'text-white' : 'text-black';
	});
</script>

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
