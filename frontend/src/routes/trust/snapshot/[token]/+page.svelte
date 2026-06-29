<script lang="ts">
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import { m } from '$paraglide/messages';
	import { donutValues } from '$lib/utils/portalResults';
	import SnapshotTreeNode from '$lib/components/TrustPortal/SnapshotTreeNode.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	const snap = $derived(data.snapshot);
	const summary = $derived(snap.summary ?? {});
	const mode = $derived(snap.display_mode ?? 'both');
	const values = $derived(donutValues(summary));

	let collapsed = $state(new Set<string>());
	function toggle(path: string) {
		const next = new Set(collapsed);
		if (next.has(path)) next.delete(path);
		else next.add(path);
		collapsed = next;
	}
	// All section (branch) paths, for expand-all / collapse-all.
	function sectionPaths(nodes: any[], prefix = ''): string[] {
		let out: string[] = [];
		(nodes ?? []).forEach((n, i) => {
			const p = prefix === '' ? String(i) : `${prefix}.${i}`;
			if ((n.children?.length ?? 0) > 0) out = [...out, p, ...sectionPaths(n.children, p)];
		});
		return out;
	}
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
							<DonutChart
								name="snapshot_donut"
								{values}
								height="h-56"
								showPercentage
								showLegend={false}
							/>
						</div>
						<div
							class="mt-3 flex flex-wrap justify-center gap-x-4 gap-y-1 text-xs text-surface-600-400"
						>
							{#each values as v}
								<span class="flex items-center gap-1.5">
									<span
										class="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
										style="background-color: {v.itemStyle.color}"
									></span>
									{v.name} ({v.value})
								</span>
							{/each}
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
			{#if (snap.content ?? []).length}
				<div class="mb-2 flex justify-end gap-3 text-xs">
					<button
						type="button"
						onclick={() => (collapsed = new Set())}
						class="text-surface-500 hover:text-primary-500">{m.expandAll()}</button
					>
					<button
						type="button"
						onclick={() => (collapsed = new Set(sectionPaths(snap.content)))}
						class="text-surface-500 hover:text-primary-500">{m.collapseAll()}</button
					>
				</div>
				{#each snap.content as root, i}
					<SnapshotTreeNode node={root} path={String(i)} {mode} {collapsed} onToggle={toggle} />
				{/each}
			{:else}
				<p class="text-sm text-surface-500">{m.noData()}</p>
			{/if}
		</div>
	</div>
</div>
