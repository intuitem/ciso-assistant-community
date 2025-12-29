<script lang="ts">
	import { ContextMenu } from 'bits-ui';
	import { m } from '$paraglide/messages';
	import { complianceResultTailwindColorMap, BASE_API_URL } from '$lib/utils/constants';

	interface Props {
		/** requirement_assessment id */
		id: string;
		/** current result */
		result: string | null;
	}

	let { id, result }: Props = $props();

	const URLModel = 'requirement-assessments';

	const options = [
		{ id: 'not_assessed', label: m.notAssessed() },
		{ id: 'non_compliant', label: m.nonCompliant() },
		{ id: 'partially_compliant', label: m.partiallyCompliant() },
		{ id: 'compliant', label: m.compliant() },
		{ id: 'not_applicable', label: m.notApplicable() }
	];
	import { page } from '$app/stores';

	const url = new URL($page.url);

	async function updateRequirementAssessment(newResult: string) {
	// optimistic update
	result = newResult;

	await fetch(`${url}/flash-mode?/updateRequirementAssessment`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			id,
			result: newResult
		})
	});
}

</script>

<ContextMenu.Label class="px-3 py-2 text-xs font-semibold text-gray-500">
	{m.changeStatus()}
</ContextMenu.Label>

{#each options as option}
	<ContextMenu.Item
		disabled={option.id === result}
		class="flex items-center justify-between gap-2 rounded-md px-3 py-2 text-sm
			data-highlighted:bg-gray-100 disabled:opacity-50"
		on:click={() => updateRequirementAssessment(option.id)}
	>
		<span>{option.label}</span>

		<span
			class="h-3 w-3 rounded-full"
			style="background-color: {complianceResultTailwindColorMap[option.id]}"
		/>
	</ContextMenu.Item>
{/each}
