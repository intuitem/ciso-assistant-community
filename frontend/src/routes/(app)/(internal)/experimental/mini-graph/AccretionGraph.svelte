<script lang="ts">
	import { onMount } from 'svelte';
	import { mountThemeAwareChart, isDarkTheme } from '$lib/utils/echartsTheme';
	import { buildGraphOption } from './option';
	import type { LiveGraph, LiveNode } from './accretion';

	interface Props {
		graph: LiveGraph;
		showLabels?: boolean;
		onNodeClick?: (node: LiveNode) => void;
		onNodeDoubleClick?: (node: LiveNode) => void;
	}

	let { graph, showLabels = true, onNodeClick, onNodeDoubleClick }: Props = $props();

	let container: HTMLDivElement;
	let chart: any = $state(null);

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
						c.on('click', (p: any) => {
							if (p.dataType !== 'node') return;
							const n = graph.nodes.get(p.data.id);
							if (n) onNodeClick?.(n);
						});
						c.on('dblclick', (p: any) => {
							if (p.dataType !== 'node') return;
							const n = graph.nodes.get(p.data.id);
							if (n) onNodeDoubleClick?.(n);
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

	// Replace rather than merge: a collapse makes the data array shorter, and
	// merging leaves the dropped nodes on screen. Stability does not depend on the
	// merge here — it comes from the coordinates, which never change once assigned.
	$effect(() => {
		chart?.setOption(buildGraphOption(graph, showLabels, isDarkTheme()), true);
	});
</script>

<div bind:this={container} class="h-full w-full"></div>
