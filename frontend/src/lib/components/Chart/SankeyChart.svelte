<script lang="ts">
	import { onMount } from 'svelte';

	import { mountThemeAwareChart } from '$lib/utils/echartsTheme';

	interface sankeyData {
		source: string;
		target: string;
		value: number;
	}
	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		title?: string;
		name?: string;
		values: sankeyData[]; // Set the types for these variables later on
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		title = '',
		name = '',
		values
	}: Props = $props();

	const chart_id = `${name}_div`;
	onMount(() => {
		let dispose: (() => void) | undefined;
		let active = true;
		(async () => {
			const echarts = await import('echarts');
			if (!active) return;
			const el = document.getElementById(chart_id);
			if (!el) return;
			dispose = mountThemeAwareChart(echarts, el, () => {
				// specify chart configuration item and data
				var option = {
					title: {
						subtext: title
					},
					series: {
						type: 'sankey',
						layout: 'none',
						orient: 'horizontal',
						emphasis: {
							focus: 'adjacency'
						},
						data: [
							{
								name: 'Controls function'
							},
							{
								name: 'Govern'
							},
							{
								name: 'Identify'
							},
							{
								name: 'Protect'
							},
							{
								name: 'Detect'
							},
							{
								name: 'Respond'
							},
							{
								name: 'Recover'
							},
							{
								name: '--'
							}
						],
						links: values
					}
				};

				// console.debug(option);

				// use configuration item and data specified to show chart
				return option;
			});
		})();
		return () => {
			active = false;
			dispose?.();
		};
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
