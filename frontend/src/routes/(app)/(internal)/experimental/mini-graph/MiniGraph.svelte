<script lang="ts">
	import { onMount } from 'svelte';
	import { mountThemeAwareChart, isDarkTheme } from '$lib/utils/echartsTheme';
	import { buildEgoGraph, type EgoNode } from './ego';
	import { buildGraphOption } from './option';
	import { TYPE_META, type NodeType } from './universe';

	interface Props {
		rootId: string;
		depth?: number;
		fanCap?: number;
		hiddenTypes?: Set<NodeType>;
		mode?: 'radial' | 'force';
		showLabels?: boolean;
		height?: string;
		onReroot?: (id: string) => void;
		onOpen?: (node: EgoNode) => void;
		onStats?: (stats: { nodes: number; links: number; truncated: number }) => void;
	}

	let {
		rootId,
		depth = 1,
		fanCap = 5,
		hiddenTypes = new Set<NodeType>(),
		mode = 'radial',
		showLabels = true,
		height = 'h-80',
		onReroot,
		onOpen,
		onStats
	}: Props = $props();

	let expanded = $state(new Set<string>());
	let selected: EgoNode | null = $state(null);
	let container: HTMLDivElement;
	let chart: any = $state(null);
	let boxWidth = $state(0);
	let boxHeight = $state(0);

	const graph = $derived(
		buildEgoGraph({
			rootId,
			depth,
			fanCap,
			hiddenTypes,
			expanded,
			aspect: boxHeight > 0 ? boxWidth / boxHeight : 1
		})
	);
	const byId = $derived(new Map(graph.nodes.map((n) => [n.id, n])));

	// Re-rooting lands on a different object: nothing about the previous selection or
	// the expansions it drove still applies.
	$effect(() => {
		rootId;
		expanded = new Set();
		selected = null;
	});

	$effect(() => {
		onStats?.({ nodes: graph.nodes.length, links: graph.links.length, truncated: graph.truncated });
	});

	function handleClick(params: any) {
		if (params.dataType !== 'node') return;
		const n = byId.get(params.data.id);
		if (!n) return;
		if (n.aggregate) {
			const next = new Set(expanded);
			next.add(n.aggregate.key);
			expanded = next;
			return;
		}
		selected = n;
	}

	onMount(() => {
		let dispose: (() => void) | undefined;
		let active = true;
		(async () => {
			const echarts = await import('echarts');
			if (!active) return;
			dispose = mountThemeAwareChart(
				echarts,
				container,
				() => buildGraphOption({ graph, mode, showLabels, dark: isDarkTheme() }),
				{
					onChart: (c) => {
						chart = c;
						c.on('click', handleClick);
						c.on('dblclick', (params: any) => {
							if (params.dataType !== 'node') return;
							const n = byId.get(params.data.id);
							if (n && !n.aggregate) onOpen?.(n);
						});
					}
				}
			);
		})();
		return () => {
			active = false;
			dispose?.();
		};
	});

	// Full rebuild on every control change — cheap at this size, and it keeps the
	// layout deterministic instead of animating out of a stale force state.
	$effect(() => {
		chart?.setOption(buildGraphOption({ graph, mode, showLabels, dark: isDarkTheme() }), true);
	});
</script>

<div class="relative {height} w-full">
	<div
		bind:this={container}
		bind:clientWidth={boxWidth}
		bind:clientHeight={boxHeight}
		class="h-full w-full"
	></div>

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
					{#if selected.depth !== 0}
						<button
							class="btn btn-sm preset-tonal"
							title="Re-centre the graph on this object"
							onclick={() => onReroot?.(selected!.id)}
							aria-label="Re-centre"><i class="fa-solid fa-crosshairs"></i></button
						>
					{/if}
					<button
						class="btn btn-sm preset-tonal"
						title="Open the object page"
						onclick={() => onOpen?.(selected!)}
						aria-label="Open"
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
