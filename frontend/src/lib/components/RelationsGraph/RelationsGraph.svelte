<script lang="ts">
	import { onMount } from 'svelte';
	import { mountThemeAwareChart, isDarkTheme } from '$lib/utils/echartsTheme';
	import { placeNeighborhood, type PlacedNode } from './layout';
	import { buildGraphOption } from './option';
	import type { Neighborhood } from './types';

	interface Props {
		data: Neighborhood;
		fanCap?: number;
		hidden?: Set<string>;
		showLabels?: boolean;
		onSelect?: (node: PlacedNode | null) => void;
		onOpen?: (node: PlacedNode) => void;
		onStats?: (stats: { nodes: number; collapsed: number }) => void;
	}

	let {
		data,
		fanCap = 5,
		hidden = new Set<string>(),
		showLabels = true,
		onSelect,
		onOpen,
		onStats
	}: Props = $props();

	let expanded = $state(new Set<string>());
	let container: HTMLDivElement;
	let chart: any = $state(null);
	let boxWidth = $state(0);
	let boxHeight = $state(0);

	const graph = $derived(
		placeNeighborhood(data, {
			fanCap,
			hidden,
			expanded,
			aspect: boxHeight > 0 ? boxWidth / boxHeight : 1
		})
	);
	const byId = $derived(new Map(graph.nodes.map((n) => [n.id, n])));

	// A new root is a different record: the expansions the previous one drove no
	// longer mean anything.
	$effect(() => {
		data.root.id;
		expanded = new Set();
	});

	$effect(() => {
		onStats?.({ nodes: graph.nodes.length - 1, collapsed: graph.collapsed });
	});

	function handleClick(params: any) {
		if (params.dataType !== 'node') return;
		const n = byId.get(params.data.id);
		if (!n) return;
		if (n.aggregate) {
			const next = new Set(expanded);
			next.add(n.aggregate.group);
			expanded = next;
			return;
		}
		onSelect?.(n);
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
				() => buildGraphOption(graph, showLabels, isDarkTheme()),
				{
					onChart: (c) => {
						chart = c;
						c.on('click', handleClick);
						c.on('dblclick', (params: any) => {
							if (params.dataType !== 'node') return;
							const n = byId.get(params.data.id);
							if (n && !n.aggregate && n.depth !== 0) onOpen?.(n);
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

	// Full rebuild on every change — cheap at this size, and it keeps the layout
	// deterministic instead of animating out of a stale state.
	$effect(() => {
		chart?.setOption(buildGraphOption(graph, showLabels, isDarkTheme()), true);
	});
</script>

<div
	bind:this={container}
	bind:clientWidth={boxWidth}
	bind:clientHeight={boxHeight}
	class="h-full w-full"
></div>
