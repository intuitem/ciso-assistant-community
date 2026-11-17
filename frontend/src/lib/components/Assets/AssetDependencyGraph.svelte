<script lang="ts">
	import { m } from '#paraglide/messages.js';
	import DependencyFlow from './DependencyFlow.svelte';
	import DependencyDomainMap from './DependencyDomainMap.svelte';
	import DependencyGapRegister from './DependencyGapRegister.svelte';
	import {
		STATUS_CLASS,
		STATUS_ORDER,
		buildGraph,
		formatValue,
		type DependencyData,
		type DependencyNode,
		type Status
	} from './dependency-graph';

	interface Props {
		data: DependencyData;
	}

	let { data }: Props = $props();

	const graph = $derived(buildGraph(data));

	let view = $state<'flow' | 'domains' | 'register'>('flow');
	let selected = $state<string | null>(null);
	let cell = $state<DependencyNode[] | null>(null);
	let prune = $derived(data.nodes.length > 150);

	const views = [
		{ id: 'flow', label: m.dependencyFlow },
		{ id: 'domains', label: m.domainMap },
		{ id: 'register', label: m.gapRegister }
	] as const;

	const statusLabel: Record<Status, () => string> = {
		cause: m.dependencyCause,
		impacted: m.dependencyImpacted,
		ok: m.objectivesMet,
		none: m.noData
	};

	const countOf = (status: Status) => graph.nodes.filter((n) => n.status === status).length;
	const stats = $derived([
		...(graph.roots.length > 1 ? [[m.assessedAssets(), graph.roots.length]] : []),
		[m.assets(), graph.nodes.length],
		[m.domains(), Object.keys(graph.domainColor).length],
		[
			m.crossDomainLinks(),
			graph.links.filter((l) => graph.byId[l.source].domain !== graph.byId[l.target].domain).length
		],
		[m.dependencyCauses(), countOf('cause')],
		[m.dependencyImpacted(), countOf('impacted')]
	]);

	const topCauses = $derived(
		graph.nodes
			.filter((n) => n.status === 'cause')
			.sort((a, b) => (graph.impacts[b.id]?.length ?? 0) - (graph.impacts[a.id]?.length ?? 0))
			.slice(0, 12)
	);

	const node = $derived(selected ? graph.byId[selected] : null);

	function select(id: string | null) {
		selected = id;
		cell = null;
		if (id && view !== 'flow') view = 'flow';
	}
</script>

{#snippet assetList(ids: string[])}
	<ul class="space-y-1">
		{#each ids as id (id)}
			{@const n = graph.byId[id]}
			<li>
				<button
					class="flex w-full items-center gap-2 rounded px-1 py-0.5 text-left hover:bg-primary-500/10"
					onclick={() => select(id)}
				>
					<span class="size-2.5 shrink-0 rounded-sm {STATUS_CLASS[n.status].bg}"></span>
					<span class="flex-1 truncate">{n.label}</span>
					<span class="size-2.5 shrink-0 rounded-sm" style:background={graph.domainColor[n.domain]}
					></span>
				</button>
			</li>
		{/each}
	</ul>
{/snippet}

<div class="space-y-3">
	<div class="flex flex-wrap items-center gap-4">
		<div class="btn-group preset-outlined-surface-200-800 p-1">
			{#each views as v (v.id)}
				<button
					class="btn btn-sm {view === v.id ? 'preset-filled-primary-500' : 'hover:preset-tonal'}"
					onclick={() => (view = v.id)}>{v.label()}</button
				>
			{/each}
		</div>
		{#if view === 'flow'}
			<label class="flex items-center gap-2 text-sm text-surface-600-400">
				<input type="checkbox" class="checkbox" bind:checked={prune} />
				{m.onlyPathsToGaps()}
			</label>
		{/if}
		<div class="ml-auto flex flex-wrap gap-5">
			{#each stats as [label, value] (label)}
				<div>
					<div class="text-xs uppercase tracking-wide text-surface-600-400">{label}</div>
					<div class="text-lg font-semibold tabular-nums">{value}</div>
				</div>
			{/each}
		</div>
	</div>

	<div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
		<div
			class="card h-[68vh] min-h-[420px] overflow-hidden border border-surface-200-800 bg-surface-50-950"
		>
			{#if view === 'flow'}
				<DependencyFlow {graph} {prune} {selected} onselect={select} />
			{:else if view === 'domains'}
				<DependencyDomainMap
					{graph}
					onselectcell={(nodes) => ((cell = nodes), (selected = null))}
				/>
			{:else}
				<DependencyGapRegister {graph} onselect={select} />
			{/if}
		</div>

		<aside
			class="card h-[68vh] min-h-[420px] min-w-0 space-y-4 overflow-auto border border-surface-200-800 bg-surface-50-950 p-4 text-sm"
		>
			{#if node}
				<div>
					<div class="text-xs uppercase tracking-wide text-surface-600-400">
						{node.type === 'PR' ? m.primary() : m.support()}
					</div>
					<h2 class="text-base font-semibold break-words">{node.label}</h2>
					<div class="mt-2 flex flex-wrap gap-2">
						<span class="badge text-xs text-white {STATUS_CLASS[node.status].bg}"
							>{statusLabel[node.status]()}</span
						>
						{#if graph.roots.includes(node.id)}
							<span class="badge preset-tonal-primary text-xs">{m.assessedAsset()}</span>
						{/if}
						<span class="badge preset-tonal text-xs" style:color={graph.domainColor[node.domain]}
							>{node.domain_name}</span
						>
					</div>
				</div>
				{#if node.gaps.length}
					<div class="grid grid-cols-[1fr_auto_auto] gap-x-3 gap-y-1 font-mono text-xs">
						<span class="text-surface-600-400">{m.objective()}</span>
						<span class="text-surface-600-400">{m.expected()}</span>
						<span class="text-surface-600-400">{m.actual()}</span>
						{#each node.gaps as gap (gap.objective)}
							<span>{gap.objective}</span>
							<span>{formatValue(gap.objective, gap.expected)}</span>
							<span class="text-error-500">{formatValue(gap.objective, gap.actual)}</span>
						{/each}
					</div>
				{/if}
				{#if node.causes.length}
					<div>
						<div class="mb-1 text-xs uppercase tracking-wide text-surface-600-400">
							{m.causedBy()} ({node.causes.length})
						</div>
						{@render assetList(node.causes)}
					</div>
				{/if}
				{#if graph.impacts[node.id]?.length}
					<div>
						<div class="mb-1 text-xs uppercase tracking-wide text-surface-600-400">
							{m.dragsDown()} ({graph.impacts[node.id].length})
						</div>
						{@render assetList(graph.impacts[node.id])}
					</div>
				{/if}
				<button class="btn btn-sm preset-tonal" onclick={() => select(null)}
					>{m.clearSelection()}</button
				>
			{:else if cell}
				<div>
					<div class="text-xs uppercase tracking-wide text-surface-600-400">
						{cell[0].domain_name}
					</div>
					<h2 class="text-base font-semibold">{m.assets()} ({cell.length})</h2>
				</div>
				{@render assetList(
					[...cell]
						.sort((a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status))
						.map((n) => n.id)
				)}
			{:else}
				<div class="space-y-2">
					<div class="text-xs uppercase tracking-wide text-surface-600-400">{m.legend()}</div>
					<div class="flex flex-wrap gap-3 text-xs">
						{#each STATUS_ORDER as status (status)}
							<span class="flex items-center gap-1"
								><span class="size-2.5 rounded-sm {STATUS_CLASS[status].bg}"></span>{statusLabel[
									status
								]()}</span
							>
						{/each}
						<span class="flex items-center gap-1"
							><span class="h-0.5 w-4 border-t-2 border-dashed border-primary-500"
							></span>{m.crossDomainLink()}</span
						>
						<span class="flex items-center gap-1"
							><span class="h-0.5 w-4 border-t-2 border-dotted border-tertiary-500"
							></span>{m.extraDependency()}</span
						>
						<span class="flex items-center gap-1"
							><span class="size-2 rounded-full bg-primary-500"></span>{m.assessedAsset()}</span
						>
					</div>
					<div class="flex flex-wrap gap-3 text-xs">
						{#each Object.entries(graph.domainColor) as [domain, color] (domain)}
							<span class="flex items-center gap-1"
								><span class="size-2.5 rounded-sm" style:background={color}></span>{graph
									.domainName[domain]}</span
							>
						{/each}
					</div>
				</div>
				<div>
					<h2 class="text-base font-semibold">{m.biggestCauses()}</h2>
					<p class="mb-2 text-surface-600-400">
						{topCauses.length ? m.selectCauseToTrace() : m.noCapabilityGaps()}
					</p>
					{@render assetList(topCauses.map((n) => n.id))}
				</div>
			{/if}
		</aside>
	</div>
</div>
