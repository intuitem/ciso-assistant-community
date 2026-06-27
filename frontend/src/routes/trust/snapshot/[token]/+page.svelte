<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { donutValues, RESULT_BY_KEY } from '$lib/utils/portalResults';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const snap = $derived(data.snapshot);
	const summary = $derived(snap.summary ?? {});
	const mode = $derived(snap.display_mode ?? 'both');
	const values = $derived(donutValues(summary));
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
			{#if mode !== 'score'}
				<div class="card bg-surface-50-950 p-5">
					{#if values.length}
						<div class="h-56">
							<DonutChart name="snapshot_donut" {values} height="h-56" showPercentage />
						</div>
					{:else}
						<p class="text-sm text-surface-500">{m.noData()}</p>
					{/if}
				</div>
			{/if}
			<div class="card flex flex-col justify-center bg-surface-50-950 p-5">
				{#if mode !== 'result' && summary.score != null}
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
						{#if mode !== 'score'}<th class="py-2 pr-3 font-medium">{m.result()}</th>{/if}
						{#if mode !== 'result'}<th class="py-2 font-medium">{m.score()}</th>{/if}
					</tr>
				</thead>
				<tbody>
					{#each snap.content ?? [] as row}
						<tr class="border-b border-surface-100-900">
							<td class="py-1.5 pr-3 font-mono text-xs text-surface-500">{row.ref_id}</td>
							<td class="py-1.5 pr-3">{row.name}</td>
							{#if mode !== 'score'}
								<td class="py-1.5 pr-3">
									<span
										class="inline-block rounded-full px-2 py-0.5 text-xs"
										style="background-color: {RESULT_BY_KEY[row.result]?.color ?? '#d1d5db'}33"
									>
										{safeTranslate(RESULT_BY_KEY[row.result]?.label ?? row.result)}
									</span>
								</td>
							{/if}
							{#if mode !== 'result'}<td class="py-1.5">{row.score ?? '—'}</td>{/if}
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>
</div>
