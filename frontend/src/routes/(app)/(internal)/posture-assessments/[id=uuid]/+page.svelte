<script lang="ts">
	import type { PageData, ActionData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import PostureTrendChart from '$lib/components/Chart/PostureTrendChart.svelte';
	import PostureHeatmapChart from '$lib/components/Chart/PostureHeatmapChart.svelte';
	import { enhance } from '$app/forms';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';
	import { postureResultTailwindColorMap } from '$lib/utils/constants';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();

	const resultLabels: Record<string, string> = {
		pass: m.pass(),
		fail: m.fail(),
		not_applicable: m.notApplicable(),
		error: m.error(),
		not_checked: m.notChecked()
	};

	const results = $derived(data.posture?.results ?? []);

	const assets = $derived.by(() => {
		const columns = (data.data?.assets ?? []).map((a: any) => ({ id: a.id, name: a.str }));
		const known = new Set(columns.map((a: any) => a.id));
		for (const row of results) {
			if (!known.has(row.asset.id)) {
				columns.push({ id: row.asset.id, name: row.asset.str });
				known.add(row.asset.id);
			}
		}
		return columns;
	});

	const checks = $derived.by(() => {
		const seen = new Map();
		for (const row of results) seen.set(row.requirement.id, row.requirement);
		return [...seen.values()].sort((a, b) =>
			(a.ref_id ?? '').localeCompare(b.ref_id ?? '', undefined, { numeric: true })
		);
	});

	const counts = $derived.by(() => {
		const acc: Record<string, number> = {};
		for (const row of results) acc[row.result] = (acc[row.result] ?? 0) + 1;
		return acc;
	});

	const trendPoints = $derived(data.trend?.points ?? []);
</script>

<div class="flex flex-col space-y-4">
	<DetailView {data}>
		{#snippet actions()}
			<Anchor
				href="/posture-assessments/{data.data.id}/tree"
				class="btn preset-filled-primary-500 h-fit w-full"
				label={m.treeView()}
			>
				<i class="fa-solid fa-folder-tree mr-2"></i>{m.treeView()}
			</Anchor>
		{/snippet}
		{#snippet widgets()}
			<div class="h-full flex flex-col space-y-4">
				<div class="card p-4 bg-surface-50-950 shadow-xs">
					<h3 class="text-lg font-semibold mb-2">{m.currentPosture()}</h3>
					<div class="grid grid-cols-2 gap-2">
						<div class="rounded-lg bg-primary-100 p-3 text-center">
							<p class="text-xs font-medium text-primary-800-200">{m.passRate()}</p>
							<p class="text-xl font-bold text-primary-900" data-testid="posture-score">
								{data.posture?.score != null ? `${data.posture.score}%` : '--'}
							</p>
						</div>
						<div class="rounded-lg bg-primary-100 p-3 text-center">
							<p class="text-xs font-medium text-primary-800-200">{m.measuredChecks()}</p>
							<p class="text-xl font-bold text-primary-900" data-testid="posture-measured">
								{checks.length}
							</p>
						</div>
					</div>
					<div class="mt-3 space-y-1">
						{#each Object.entries(resultLabels) as [value, label]}
							{#if counts[value]}
								<div class="flex items-center justify-between text-sm">
									<span class="flex items-center gap-2">
										<span
											class="inline-block w-3 h-3 rounded-sm {postureResultTailwindColorMap[value]}"
										></span>
										{label}
									</span>
									<span class="font-semibold">{counts[value]}</span>
								</div>
							{/if}
						{/each}
					</div>
				</div>
			</div>
		{/snippet}
	</DetailView>

	{#if trendPoints.length > 1}
		<div class="card p-4 bg-surface-50-950 shadow-xs">
			<h3 class="text-lg font-semibold mb-2">{m.passRate()}</h3>
			<PostureTrendChart points={trendPoints} name="posture_trend" />
		</div>
	{/if}

	{#if results.length}
		<div class="card p-4 bg-surface-50-950 shadow-xs">
			<h3 class="text-lg font-semibold mb-2">{m.currentPosture()}</h3>
			<PostureHeatmapChart {results} {assets} name="posture_heatmap" />
		</div>
	{/if}

	{#if data.actionPlan?.total_fails}
		<div class="card p-4 bg-surface-50-950 shadow-xs">
			<div class="flex items-center justify-between mb-4">
				<h3 class="text-lg font-semibold">{m.actionPlan()}</h3>
				<p class="text-sm text-surface-600-400">
					{data.actionPlan.total_fails}
					{m.fail()} — {data.actionPlan.planned}
					{m.planned()}, {data.actionPlan.total_fails - data.actionPlan.planned}
					{m.unplanned()}
				</p>
			</div>
			<div class="overflow-x-auto">
				<table class="table-auto w-full text-sm">
					<thead>
						<tr class="text-left">
							<th class="px-2 py-1"></th>
							<th class="px-2 py-1">{m.assets()}</th>
							<th class="px-2 py-1">{m.observedValue()}</th>
							<th class="px-2 py-1">{m.actionPlan()}</th>
						</tr>
					</thead>
					<tbody>
						{#each data.actionPlan.results as row (`${row.requirement.id}:${row.asset.id}`)}
							<tr class="border-t border-surface-200-800 align-top">
								<td class="px-2 py-2 font-medium whitespace-nowrap" title={row.requirement.name}>
									{row.requirement.ref_id}
									<span class="font-normal text-surface-600-400 hidden lg:inline">
										{row.requirement.name?.length > 50
											? `${row.requirement.name.slice(0, 50)}…`
											: (row.requirement.name ?? '')}
									</span>
								</td>
								<td class="px-2 py-2 whitespace-nowrap">{row.asset.str}</td>
								<td class="px-2 py-2 text-surface-600-400">
									{[row.actual, row.expected ? `(expected: ${row.expected})` : '', row.message]
										.filter(Boolean)
										.join(' ') || '--'}
								</td>
								<td class="px-2 py-2">
									{#if row.finding}
										<div class="flex items-center gap-2 flex-wrap">
											<Anchor
												href="/findings/{row.finding.id}"
												class="anchor whitespace-nowrap"
												label={row.finding.name}
											>
												{row.finding.name}
											</Anchor>
											<span class="badge preset-tonal-secondary text-xs">
												{safeTranslate(row.finding.status)}
											</span>
											{#if row.finding.eta}
												<span class="text-xs text-surface-600-400"
													>{m.eta()}: {row.finding.eta}</span
												>
											{/if}
										</div>
									{:else}
										<form method="POST" action="?/createFinding" use:enhance>
											<input type="hidden" name="requirement" value={row.requirement.id} />
											<input type="hidden" name="asset" value={row.asset.id} />
											<button type="submit" class="btn btn-sm preset-filled-primary-500">
												<i class="fa-solid fa-clipboard-list mr-2"></i>{m.createFinding()}
											</button>
										</form>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}
</div>
