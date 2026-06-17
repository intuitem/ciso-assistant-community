<script lang="ts">
	import { onMount } from 'svelte';

	import { mountThemeAwareChart } from '$lib/utils/echartsTheme';
	import { safeTranslate } from '$lib/utils/i18n';

	import { level } from '$paraglide/messages';
	interface riskChartData {
		name: string;
		value: number;
		color: string;
	}

	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		title?: string;
		name: string;
		values: riskChartData[]; // Set the types for these variables later on
		colors?: string[];
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		title = '',
		name,
		values = $bindable(),
		colors = []
	}: Props = $props();

	for (const index in values) {
		if (values[index].name) {
			values[index].name = safeTranslate(values[index].name);
		}
	}
	const chart_id = `${name}_div`;
	onMount(() => {
		let dispose: (() => void) | undefined;
		let active = true;
		(async () => {
			const echarts = await import('echarts');
			if (!active) return;
			const el = document.getElementById(chart_id);
			if (!el) return;
			dispose = mountThemeAwareChart(echarts, el, () => ({
				title: {
					subtext: title
				},
				tooltip: {
					trigger: 'item'
				},
				series: [
					{
						name: level(),
						type: 'pie',
						radius: ['40%', '70%'],
						center: ['50%', '70%'],
						// adjust the start and end angle
						startAngle: 180,
						endAngle: 360,
						minShowLabelAngle: 1,
						data: values,
						color: colors
					}
				]
			}));
		})();
		return () => {
			active = false;
			dispose?.();
		};
	});
</script>

<div id={chart_id} class="{width} {height} {classesContainer}"></div>
