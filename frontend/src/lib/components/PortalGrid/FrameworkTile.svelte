<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	let { item, onTrigger }: { item: any; onTrigger?: (item: any) => void } = $props();

	const snap = $derived(item.snapshot);
	const summary = $derived(snap?.summary ?? {});

	const RESULT_META = [
		{ key: 'compliant', label: 'compliant', color: '#86efac' },
		{ key: 'partially_compliant', label: 'partiallyCompliant', color: '#fde047' },
		{ key: 'non_compliant', label: 'nonCompliant', color: '#f87171' },
		{ key: 'not_applicable', label: 'notApplicable', color: '#000000' },
		{ key: 'not_assessed', label: 'notAssessed', color: '#d1d5db' }
	];

	const values = $derived(
		RESULT_META.map((r) => ({
			name: safeTranslate(r.label),
			value: summary[r.key] ?? 0,
			itemStyle: { color: r.color }
		})).filter((v) => v.value > 0)
	);
</script>

{#if snap}
	<div
		role="button"
		tabindex="0"
		onclick={() => onTrigger?.(item)}
		onkeydown={(e) => {
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				onTrigger?.(item);
			}
		}}
		class="flex flex-col gap-2 rounded-2xl border border-surface-200-800 bg-surface-50-950 p-5 shadow-sm transition-all hover:border-violet-400 hover:shadow-md cursor-pointer"
	>
		<div class="flex items-center justify-between">
			<div class="font-semibold text-surface-800-200">
				{safeTranslate(item.title) || snap.framework_name}
			</div>
			{#if summary.score != null}
				<span class="text-sm font-bold text-violet-600"
					>{summary.score}{#if summary.max_score}<span class="text-surface-400"
							>/{summary.max_score}</span
						>{/if}</span
				>
			{/if}
		</div>
		{#if values.length}
			<div class="h-40">
				<DonutChart name={`fw_${snap.token}`} {values} height="h-40" />
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
