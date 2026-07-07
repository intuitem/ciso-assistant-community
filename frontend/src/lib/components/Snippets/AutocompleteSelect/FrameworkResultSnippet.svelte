<script lang="ts">
	import { complianceResultColorMap, complianceResultTailwindColorMap } from '$lib/utils/constants';

	interface Props {
		option: Record<string, any>;
		idx?: number | undefined;
	}
	let { option }: Props = $props();

	const REQUIREMENT_ASSESSMENT_RESULT = [
		'compliant',
		'non_compliant',
		'partially_compliant',
		'not_applicable'
	] as const;

	type ResultPercentage = {
		result: (typeof REQUIREMENT_ASSESSMENT_RESULT)[number];
		percentage: {
			value: number;
			display: string;
		};
	};

	let resultCounts = $derived(option.results);

	const orderedResultPercentages: ResultPercentage[] = REQUIREMENT_ASSESSMENT_RESULT.map(
		(result) => {
			if (!resultCounts) return { result: result, percentage: { value: 0, display: '0' } };
			const value = resultCounts[result] || 0;
			const percentValue: number = (value / option.assessable_requirements_count) * 100;
			const percentage = {
				value: percentValue,
				display: percentValue.toFixed(0)
			};
			return { result: result, percentage };
		}
	);
</script>

<span class="w-full">
	{option.label}
	<div class="flex grow bg-surface-200-800 rounded-md overflow-hidden h-4 shrink self-center">
		{#each orderedResultPercentages as rp}
			<div
				class="flex flex-col justify-center overflow-hidden text-xs text-center {complianceResultTailwindColorMap[
					rp.result
				]}"
				style="width: {rp.percentage.value}%; background-color: {complianceResultColorMap[
					rp.result
				]}"
			>
				{rp.percentage.display}%
			</div>
		{/each}
	</div>
</span>
