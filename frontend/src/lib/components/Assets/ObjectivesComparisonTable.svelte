<script lang="ts">
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { SECURITY_OBJECTIVE_SCALE_MAP } from '$lib/utils/constants';
	import { page } from '$app/state';

	interface Props {
		comparisons: any[];
		title: string;
		icon: string;
		uppercaseLabels?: boolean;
	}

	let { comparisons, title, icon, uppercaseLabels = false }: Props = $props();

	const scale = page.data.settings?.security_objective_scale || '1-4';
	const scaleMap = SECURITY_OBJECTIVE_SCALE_MAP[scale];

	const getDisplayValue = (rawValue: number | null | undefined): string => {
		if (rawValue === null || rawValue === undefined) return '--';
		if (typeof rawValue === 'number' && rawValue >= 0 && rawValue <= 4) {
			return scaleMap[rawValue];
		}
		return String(rawValue);
	};
</script>

<div class="mb-6">
	<div class="font-serif font-bold mb-3">
		<i class="fa-solid {icon} mr-2"></i>
		{title}
	</div>
	{#if comparisons?.length > 0}
		<div class="overflow-x-auto">
			<table class="min-w-full bg-surface-50-950 border border-surface-200-800 rounded-lg">
				<thead class="bg-surface-100-900">
					<tr>
						<th class="px-4 py-2 text-left text-sm font-semibold text-surface-700-300 border-b"></th>
						<th class="px-4 py-2 text-left text-sm font-semibold text-surface-700-300 border-b"
							>{m.objective()}</th
						>
						<th class="px-4 py-2 text-left text-sm font-semibold text-surface-700-300 border-b"
							>{m.capability()}</th
						>
						<th class="px-4 py-2 text-center text-sm font-semibold text-surface-700-300 border-b"
							>{m.alignment()}</th
						>
					</tr>
				</thead>
				<tbody>
					{#each comparisons as comparison}
						<tr class="border-b hover:bg-surface-50-950">
							<td class="px-4 py-2 text-sm text-surface-950-50" class:uppercase={uppercaseLabels}
								>{safeTranslate(comparison.objective)}</td
							>
							<td class="px-4 py-2 text-sm text-surface-700-300"
								>{getDisplayValue(comparison.expectation)}</td
							>
							<td class="px-4 py-2 text-sm text-surface-700-300">{getDisplayValue(comparison.reality)}</td>
							<td class="px-4 py-2 text-center">
								<span
									class="inline-flex items-center justify-center w-6 h-6 rounded-full"
									class:bg-green-500={comparison.verdict === true}
									class:bg-red-500={comparison.verdict === false}
									class:bg-surface-400-600={comparison.verdict === null}
								>
									{#if comparison.verdict === true}
										<i class="fa-solid fa-check text-white text-xs"></i>
									{:else if comparison.verdict === false}
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
	{:else}
		<div class="bg-surface-50-950 border border-surface-200-800 rounded-lg p-8 flex items-center justify-center">
			<p class="text-surface-600-400 text-center">{m.noDataAvailable()}</p>
		</div>
	{/if}
</div>
