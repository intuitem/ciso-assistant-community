<script lang="ts">
	import { fly } from 'svelte/transition';
	import AccretionGraph from './AccretionGraph.svelte';
	import {
		createGraph,
		expand,
		collapse,
		openAggregate,
		NODE_BUDGET,
		type LiveGraph,
		type LiveNode
	} from './accretion';
	import { TYPE_META, type NodeType } from './universe';

	interface Props {
		open: boolean;
		rootId: string;
		onClose: () => void;
		onOpenObject?: (node: LiveNode) => void;
	}

	let { open, rootId, onClose, onOpenObject }: Props = $props();

	let fanCap = $state(5);
	let showLabels = $state(true);
	let wide = $state(false);
	let filterOpen = $state(false);
	let hidden = $state(new Set<NodeType>(['folder']));
	let selected: LiveNode | null = $state(null);
	let graph: LiveGraph = $state(createGraph(rootId));

	const options = $derived({ fanCap, hidden });
	const expandableCount = $derived(
		[...graph.nodes.values()].filter((n) => !n.expanded && !n.exhausted && !n.aggregate).length
	);
	const root = $derived(graph.nodes.get(rootId));
	const rootMeta = $derived(TYPE_META[root?.type ?? 'applied-control']);

	// Opening on a different record starts a new exploration.
	$effect(() => {
		rootId;
		reset();
	});

	function reset() {
		graph = expand(createGraph(rootId), rootId, { fanCap, hidden });
		selected = null;
	}

	function toggle(node: LiveNode) {
		selected = node.aggregate ? null : node;
		if (node.aggregate) {
			graph = openAggregate(graph, node.id, options);
		} else if (node.expanded) {
			graph = collapse(graph, node.id);
		} else if (!node.exhausted) {
			graph = expand(graph, node.id, options);
		}
	}

	/** Only offered while the fan-out is small enough to stay readable. */
	function expandAll() {
		let next = graph;
		for (const node of [...graph.nodes.values()]) {
			if (node.expanded || node.exhausted || node.aggregate) continue;
			next = expand(next, node.id, options);
			if (next.notice) break;
		}
		graph = next;
	}

	function toggleType(t: NodeType) {
		const next = new Set(hidden);
		next.has(t) ? next.delete(t) : next.add(t);
		hidden = next;
		reset();
	}

	const LEGEND_TYPES = Object.keys(TYPE_META) as NodeType[];
</script>

<svelte:window
	onkeydown={(e) => {
		if (e.key === 'Escape' && open) onClose();
	}}
/>

{#if open}
	<aside
		class="fixed top-0 right-0 bottom-0 z-50 flex flex-col bg-surface-50-950 border-l-2 border-surface-300-700
			shadow-[-16px_0_48px_-12px_rgba(2,6,23,0.38)] dark:shadow-[-16px_0_48px_-12px_rgba(0,0,0,0.75)]"
		style="width: min({wide ? '1100px' : '580px'}, 96vw)"
		transition:fly={{ x: 420, duration: 220 }}
		aria-label="Relations"
	>
		<header class="flex items-start gap-2 p-3 border-b border-surface-200-800">
			<i class="fa-solid {rootMeta.icon} mt-1.5" style="color:{rootMeta.color}"></i>
			<div class="flex-1 min-w-0">
				<div class="text-xs text-surface-500">{rootMeta.label}</div>
				<div class="font-semibold truncate">{root?.name ?? ''}</div>
			</div>
			<button class="btn btn-sm preset-tonal" onclick={reset} title="Reset" aria-label="Reset">
				<i class="fa-solid fa-rotate-left"></i>
			</button>
			<button
				class="btn btn-sm preset-tonal"
				onclick={() => (wide = !wide)}
				title={wide ? 'Narrow' : 'Widen'}
				aria-label="Toggle width"
			>
				<i class="fa-solid {wide ? 'fa-right-to-bracket' : 'fa-left-right'}"></i>
			</button>
			<button class="btn btn-sm preset-tonal" onclick={onClose} title="Close" aria-label="Close">
				<i class="fa-solid fa-xmark"></i>
			</button>
		</header>

		<div class="relative flex-1 min-h-0 bg-surface-100-900">
			<AccretionGraph
				{graph}
				{showLabels}
				onNodeClick={toggle}
				onNodeDoubleClick={(n) => !n.aggregate && onOpenObject?.(n)}
			/>

			{#if graph.notice}
				<div
					class="absolute top-2 left-2 right-2 card preset-tonal-warning px-3 py-2 text-xs shadow-lg"
				>
					{graph.notice}
				</div>
			{/if}

			{#if selected}
				{@const meta = TYPE_META[selected.type]}
				<div
					class="absolute bottom-2 left-2 right-2 card bg-surface-50-950 border border-surface-200-800 shadow-lg p-3 text-sm"
				>
					<div class="flex items-start gap-2">
						<i class="fa-solid {meta.icon} mt-1" style="color:{meta.color}"></i>
						<div class="flex-1 min-w-0">
							<div class="text-xs text-surface-500">{meta.label}</div>
							<div class="font-semibold truncate">{selected.name}</div>
							{#if selected.meta}
								<div class="flex flex-wrap gap-x-3 gap-y-0.5 mt-1 text-xs text-surface-600-400">
									{#each Object.entries(selected.meta) as [k, v]}
										<span><span class="opacity-60">{k}:</span> {v}</span>
									{/each}
								</div>
							{/if}
						</div>
						<div class="flex items-center gap-1">
							<button
								class="btn btn-sm preset-tonal"
								title="Open the object page"
								aria-label="Open"
								onclick={() => onOpenObject?.(selected!)}
								><i class="fa-solid fa-arrow-up-right-from-square"></i></button
							>
							<button
								class="btn btn-sm preset-tonal"
								title="Close"
								aria-label="Close"
								onclick={() => (selected = null)}><i class="fa-solid fa-xmark"></i></button
							>
						</div>
					</div>
				</div>
			{/if}
		</div>

		<footer class="border-t border-surface-200-800 px-3 py-2">
			<div class="flex flex-wrap items-center gap-2 text-xs text-surface-500">
				<span class="tabular-nums">{graph.nodes.size}/{NODE_BUDGET} nodes</span>
				{#if expandableCount}
					<span class="opacity-70">· {expandableCount} expandable</span>
				{/if}
				<div class="flex-1"></div>
				{#if expandableCount && expandableCount <= 10}
					<button class="btn btn-sm preset-tonal" onclick={expandAll}>
						<i class="fa-solid fa-arrows-left-right-to-line mr-1"></i>expand all
					</button>
				{/if}
				<span class="uppercase tracking-wide">Fan-out</span>
				<input
					type="range"
					min="2"
					max="12"
					bind:value={fanCap}
					onchange={reset}
					class="w-16 accent-primary-500"
				/>
				<span class="w-4 text-center tabular-nums">{fanCap}</span>
				<button
					class="btn btn-sm preset-tonal"
					onclick={() => (showLabels = !showLabels)}
					title="Labels"
					aria-label="Toggle labels"
				>
					<i class="fa-solid fa-tag {showLabels ? '' : 'opacity-40'}"></i>
				</button>
				<button class="btn btn-sm preset-tonal" onclick={() => (filterOpen = !filterOpen)}>
					<i class="fa-solid fa-filter"></i>
					{#if hidden.size}<span class="ml-1">{hidden.size}</span>{/if}
				</button>
			</div>
			{#if filterOpen}
				<div class="flex flex-wrap gap-1 mt-2">
					{#each LEGEND_TYPES as t}
						{@const tm = TYPE_META[t]}
						{@const off = hidden.has(t)}
						<button
							class="text-[10px] px-1.5 py-0.5 rounded-full border transition {off
								? 'opacity-35 border-surface-300-700'
								: 'border-transparent'}"
							style={off ? '' : `background:${tm.color}22;color:${tm.color}`}
							onclick={() => toggleType(t)}
						>
							{tm.label}
						</button>
					{/each}
				</div>
			{/if}
		</footer>
	</aside>
{/if}
