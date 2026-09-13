<script lang="ts">
	import { fly } from 'svelte/transition';
	import MiniGraph from './MiniGraph.svelte';
	import { NODE_BY_ID, TYPE_META, type NodeType } from './universe';
	import type { EgoNode } from './ego';

	interface Props {
		open: boolean;
		rootId: string;
		onClose: () => void;
		onOpenObject?: (node: EgoNode) => void;
	}

	let { open, rootId, onClose, onOpenObject }: Props = $props();

	// The panel owns its own root so re-centring never navigates the page behind it;
	// null means "still showing the record the page is on".
	let exploredId: string | null = $state(null);
	const currentId = $derived(exploredId ?? rootId);
	let history: string[] = $state([]);
	let depth = $state(1);
	let fanCap = $state(5);
	let mode: 'radial' | 'force' = $state('radial');
	let showLabels = $state(true);
	let wide = $state(false);
	let legendOpen = $state(false);
	let hiddenTypes = $state(new Set<NodeType>(['folder']));
	let stats = $state({ nodes: 0, links: 0, truncated: 0 });

	// Opening the panel on a different object resets the exploration trail.
	$effect(() => {
		rootId;
		exploredId = null;
		history = [];
	});

	const current = $derived(NODE_BY_ID.get(currentId)!);
	const meta = $derived(TYPE_META[current.type]);

	function reroot(id: string) {
		history = [...history, currentId];
		exploredId = id;
	}
	function back() {
		if (!history.length) return;
		exploredId = history[history.length - 1];
		history = history.slice(0, -1);
	}
	function toggleType(t: NodeType) {
		const next = new Set(hiddenTypes);
		next.has(t) ? next.delete(t) : next.add(t);
		hiddenTypes = next;
	}

	const LEGEND_TYPES = Object.keys(TYPE_META) as NodeType[];
</script>

<svelte:window
	onkeydown={(e) => {
		if (e.key === 'Escape' && open) onClose();
	}}
/>

{#if open}
	<!-- No backdrop on purpose: the point of the panel is to read it against the
	     record it belongs to, so the detail view stays visible and usable. -->
	<aside
		class="fixed top-0 right-0 bottom-0 z-50 flex flex-col bg-surface-50-950 border-l border-surface-200-800 shadow-2xl"
		style="width: min({wide ? '1100px' : '460px'}, 96vw)"
		transition:fly={{ x: 420, duration: 220 }}
		aria-label="Relations"
	>
		<header class="flex items-start gap-2 p-3 border-b border-surface-200-800">
			{#if history.length}
				<button class="btn btn-sm preset-tonal" onclick={back} title="Back" aria-label="Back">
					<i class="fa-solid fa-arrow-left"></i>
				</button>
			{/if}
			<i class="fa-solid {meta.icon} mt-1.5" style="color:{meta.color}"></i>
			<div class="flex-1 min-w-0">
				<div class="text-xs text-surface-500">{meta.label}</div>
				<div class="font-semibold truncate" title={current.name}>{current.name}</div>
			</div>
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

		<div class="flex flex-wrap items-center gap-2 px-3 py-2 text-sm border-b border-surface-200-800">
			<span class="text-surface-500 text-xs uppercase tracking-wide">Depth</span>
			{#each [1, 2, 3] as d}
				<button
					class="btn btn-sm {depth === d ? 'preset-filled-primary-500' : 'preset-tonal'}"
					onclick={() => (depth = d)}>{d}</button
				>
			{/each}
			<span class="text-surface-500 text-xs uppercase tracking-wide ml-2">Fan-out</span>
			<input type="range" min="2" max="12" bind:value={fanCap} class="w-20 accent-primary-500" />
			<span class="w-4 text-center tabular-nums text-xs">{fanCap}</span>
			<button
				class="btn btn-sm preset-tonal"
				onclick={() => (mode = mode === 'radial' ? 'force' : 'radial')}
				title="Layout"
			>
				<i class="fa-solid {mode === 'radial' ? 'fa-bullseye' : 'fa-atom'}"></i>
			</button>
			<button
				class="btn btn-sm preset-tonal"
				onclick={() => (showLabels = !showLabels)}
				title="Labels"
				aria-label="Toggle labels"
			>
				<i class="fa-solid fa-tag {showLabels ? '' : 'opacity-40'}"></i>
			</button>
		</div>

		<div class="flex-1 min-h-0 p-1">
			<MiniGraph
				rootId={currentId}
				{depth}
				{fanCap}
				{mode}
				{showLabels}
				{hiddenTypes}
				height="h-full"
				onReroot={reroot}
				onOpen={onOpenObject}
				onStats={(s) => (stats = s)}
			/>
		</div>

		<footer class="border-t border-surface-200-800 px-3 py-2">
			<div class="flex items-center gap-2 text-xs text-surface-500">
				<span class="tabular-nums">
					{stats.nodes} nodes · {stats.links} edges{stats.truncated
						? ` · ${stats.truncated} collapsed`
						: ''}
				</span>
				<div class="flex-1"></div>
				<button class="btn btn-sm preset-tonal" onclick={() => (legendOpen = !legendOpen)}>
					<i class="fa-solid fa-filter mr-1"></i>types
					{#if hiddenTypes.size}<span class="ml-1 opacity-70">({hiddenTypes.size} hidden)</span>{/if}
				</button>
			</div>
			{#if legendOpen}
				<div class="flex flex-wrap gap-1 mt-2">
					{#each LEGEND_TYPES as t}
						{@const tm = TYPE_META[t]}
						{@const off = hiddenTypes.has(t)}
						<button
							class="text-[10px] px-1.5 py-0.5 rounded-full border transition {off
								? 'opacity-35 border-surface-300-700'
								: 'border-transparent'}"
							style={off ? '' : `background:${tm.color}22;color:${tm.color}`}
							onclick={() => toggleType(t)}
							title={off ? 'Show' : 'Hide'}
						>
							{tm.label}
						</button>
					{/each}
				</div>
			{/if}
		</footer>
	</aside>
{/if}
