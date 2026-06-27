<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { donutValues } from '$lib/utils/portalResults';
	import { onActivateKey } from '$lib/utils/portalActions';

	let { item, onTrigger }: { item: any; onTrigger?: (item: any) => void } = $props();

	const snap = $derived(item.snapshot);
	const summary = $derived(snap?.summary ?? {});
	const mode = $derived(snap?.display_mode ?? 'both');
	const values = $derived(donutValues(summary));
</script>

{#if snap}
	<div
		role="button"
		tabindex="0"
		onclick={() => onTrigger?.(item)}
		onkeydown={onActivateKey(() => onTrigger?.(item))}
		class="flex flex-col gap-2 rounded-2xl border border-surface-200-800 bg-surface-50-950 p-5 shadow-sm transition-all hover:border-violet-400 hover:shadow-md cursor-pointer"
	>
		<div class="flex items-center justify-between">
			<div class="font-semibold text-surface-800-200">
				{safeTranslate(item.title) || snap.framework_name}
			</div>
			{#if mode !== 'result' && summary.score != null}
				<span class="text-sm font-bold text-violet-600"
					>{summary.score}{#if summary.max_score}<span class="text-surface-400"
							>/{summary.max_score}</span
						>{/if}</span
				>
			{/if}
		</div>
		{#if mode !== 'score' && values.length}
			<div class="h-36">
				<DonutChart
					name={`fw_${snap.token}`}
					{values}
					height="h-36"
					showPercentage
					showLegend={false}
				/>
			</div>
			<div class="flex flex-wrap justify-center gap-x-3 gap-y-1 text-[10px] text-surface-600-400">
				{#each values as v}
					<span class="flex items-center gap-1">
						<span
							class="inline-block h-2 w-2 shrink-0 rounded-full"
							style="background-color: {v.itemStyle.color}"
						></span>
						{v.name} ({v.value})
					</span>
				{/each}
			</div>
		{/if}
		<div class="text-xs text-surface-500">
			{summary.requirement_count ?? 0}
			{m.requirements()}
		</div>
	</div>
{:else}
	<div
		class="flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-surface-300-700 bg-surface-50-950 p-5 text-center text-sm text-surface-500"
	>
		<i class="fa-solid fa-chart-pie text-2xl text-surface-400"></i>
		{item.title || m.framework()}
	</div>
{/if}
