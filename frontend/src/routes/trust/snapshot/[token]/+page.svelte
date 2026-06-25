<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const snap = $derived(data.snapshot);
	const summary = $derived(snap.summary ?? {});

	const RESULT_META: Record<string, { label: string; color: string }> = {
		compliant: { label: 'compliant', color: '#86efac' },
		partially_compliant: { label: 'partiallyCompliant', color: '#fde047' },
		non_compliant: { label: 'nonCompliant', color: '#f87171' },
		not_applicable: { label: 'notApplicable', color: '#000000' },
		not_assessed: { label: 'notAssessed', color: '#d1d5db' }
	};

	const values = $derived(
		Object.entries(RESULT_META)
			.map(([key, meta]) => ({
				name: safeTranslate(meta.label),
				value: summary[key] ?? 0,
				itemStyle: { color: meta.color }
			}))
			.filter((v) => v.value > 0)
	);
</script>

<svelte:head>
	<title>{snap.framework_name || snap.name}</title>
</svelte:head>

<div class="min-h-screen bg-linear-to-br from-surface-100-900 to-surface-200-800">
	<div class="mx-auto max-w-5xl px-6 py-10 space-y-8">
		<div class="flex items-center gap-3">
			<a href="/trust" class="text-surface-500 hover:text-primary-500">
				<i class="fa-solid fa-arrow-left"></i>
			</a>
			<div>
				<h1 class="text-2xl font-bold text-surface-900-100">
					{snap.framework_name || snap.name}
				</h1>
				{#if snap.synced_at}
					<p class="text-xs text-surface-500">
						{m.lastSynced()}: {new Date(snap.synced_at).toLocaleString()}
					</p>
				{/if}
			</div>
		</div>

		<div class="grid gap-6 sm:grid-cols-2">
			<div class="card bg-surface-50-950 p-5">
				{#if values.length}
					<div class="h-56"><DonutChart name="snapshot_donut" {values} height="h-56" /></div>
				{:else}
					<p class="text-sm text-surface-500">{m.noData()}</p>
				{/if}
			</div>
			<div class="card flex flex-col justify-center bg-surface-50-950 p-5">
				{#if summary.score != null}
					<div class="text-4xl font-bold text-violet-600">
						{summary.score}{#if summary.max_score}<span class="text-lg text-surface-400"
								>/{summary.max_score}</span
							>{/if}
					</div>
					<div class="text-sm text-surface-500">{m.score()}</div>
				{/if}
				<div class="mt-2 text-sm text-surface-600-400">
					{summary.requirement_count ?? 0}
					{m.requirements()}
				</div>
				<div class="mt-4 flex gap-2">
					<a
						href={`/trust/snapshot/${data.token}/export?format=csv`}
						class="btn btn-sm preset-tonal"
					>
						<i class="fa-solid fa-file-csv mr-1"></i>CSV
					</a>
					<a
						href={`/trust/snapshot/${data.token}/export?format=xlsx`}
						class="btn btn-sm preset-tonal"
					>
						<i class="fa-solid fa-file-excel mr-1"></i>Excel
					</a>
				</div>
			</div>
		</div>

		<div class="card bg-surface-50-950 p-5">
			<table class="w-full text-sm">
				<thead>
					<tr class="border-b border-surface-200-800 text-left text-surface-500">
						<th class="py-2 pr-3 font-medium">{m.refId()}</th>
						<th class="py-2 pr-3 font-medium">{m.name()}</th>
						<th class="py-2 pr-3 font-medium">{m.result()}</th>
						<th class="py-2 font-medium">{m.score()}</th>
					</tr>
				</thead>
				<tbody>
					{#each snap.content ?? [] as row}
						<tr class="border-b border-surface-100-900">
							<td class="py-1.5 pr-3 font-mono text-xs text-surface-500">{row.ref_id}</td>
							<td class="py-1.5 pr-3">{row.name}</td>
							<td class="py-1.5 pr-3">
								<span
									class="inline-block rounded-full px-2 py-0.5 text-xs"
									style="background-color: {RESULT_META[row.result]?.color ?? '#d1d5db'}33"
								>
									{safeTranslate(RESULT_META[row.result]?.label ?? row.result)}
								</span>
							</td>
							<td class="py-1.5">{row.score ?? '—'}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>
</div>
