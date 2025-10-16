<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		comparisons: any[];
		title: string;
		icon: string;
		uppercaseLabels?: boolean;
	}

	let { comparisons, title, icon, uppercaseLabels = false }: Props = $props();
</script>

{#if comparisons?.length > 0}
	<div class="mb-6">
		<div class="font-serif font-bold mb-3">
			<i class="fa-solid {icon} mr-2"></i>
			{title}
		</div>
		<div class="overflow-x-auto">
			<table class="min-w-full bg-white border border-gray-200 rounded-lg">
				<thead class="bg-gray-100">
					<tr>
						<th class="px-4 py-2 text-left text-sm font-semibold text-gray-700 border-b"></th>
						<th class="px-4 py-2 text-left text-sm font-semibold text-gray-700 border-b"
							>{m.objective()}</th
						>
						<th class="px-4 py-2 text-left text-sm font-semibold text-gray-700 border-b"
							>{m.capability()}</th
						>
						<th class="px-4 py-2 text-center text-sm font-semibold text-gray-700 border-b"
							>{m.alignment()}</th
						>
					</tr>
				</thead>
				<tbody>
					{#each comparisons as comparison}
						<tr class="border-b hover:bg-gray-50">
							<td class="px-4 py-2 text-sm text-gray-900" class:uppercase={uppercaseLabels}
								>{safeTranslate(comparison.objective)}</td
							>
							<td class="px-4 py-2 text-sm text-gray-700">{comparison.expectation || '--'}</td>
							<td class="px-4 py-2 text-sm text-gray-700">{comparison.reality || '--'}</td>
							<td class="px-4 py-2 text-center">
								<span
									class="inline-flex items-center justify-center w-6 h-6 rounded-full"
									class:bg-green-500={comparison.verdict === 'success'}
									class:bg-red-500={comparison.verdict === 'danger'}
									class:bg-gray-400={comparison.verdict === null}
								>
									{#if comparison.verdict === 'success'}
										<i class="fa-solid fa-check text-white text-xs"></i>
									{:else if comparison.verdict === 'danger'}
										<i class="fa-solid fa-xmark text-white text-xs"></i>
									{:else}
										<i class="fa-solid fa-minus text-white text-xs"></i>
									{/if}
								</span>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>
{/if}
