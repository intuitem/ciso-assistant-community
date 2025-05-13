<script lang="ts">
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';
	interface Props {
		width?: string;
		height?: string;
		classesContainer?: string;
		data: any;
		names: any;
		uuids: any;
	}

	let {
		width = 'w-auto',
		height = 'h-full',
		classesContainer = '',
		data,
		names,
		uuids
	}: Props = $props();

	function truncateString(maxLength: number) {
		return (name) => (name.length > maxLength ? name.substring(0, maxLength) + '...' : name);
	}

	const chart_id = `stacked_div`;

	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });
		const rawData = data;
		const auditTotals = rawData.map((audit) => audit.reduce((sum, val) => sum + val, 0));
		chart.on('click', function (params) {
			const index = params.dataIndex;
			if (index !== undefined && uuids && uuids[index]) {
				window.open(`/compliance-assessments/${uuids[index]}`, '_blank');
			}
		});

		const grid = {
			left: 150,
			right: 10,
			top: 50,
			bottom: 50
		};

		const seriesNames = [
			'not assessed',
			'partially compliant',
			'non compliant',
			'compliant',
			'not applicable'
		];

		// Map the internal names to translated labels
		const getSeriesLabel = (name: string) => {
			switch (name) {
				case 'not assessed':
					return m.notAssessed();
				case 'partially compliant':
					return m.partiallyCompliant();
				case 'non compliant':
					return m.nonCompliant();
				case 'compliant':
					return m.compliant();
				case 'not applicable':
					return m.notApplicable();
				default:
					return name;
			}
		};

		const series = seriesNames.map((name, categoryIdx) => {
			return {
				name,
				type: 'bar',
				stack: 'total',
				barWidth: '70%',
				label: {
					show: true,
					formatter: (params) => {
						const percentage = Math.round(params.value * 100);
						return percentage < 1 ? '' : percentage + '%';
					}
				},
				data: rawData.map((audit, auditIdx) =>
					auditTotals[auditIdx] <= 0 ? 0 : audit[categoryIdx] / auditTotals[auditIdx]
				)
			};
		});

		var option = {
			color: ['#d7dfea', '#74C0DE', '#E66', '#91CC75', '#EAE2D7'],
			legend: {
				selectedMode: false,
				formatter: (name) => getSeriesLabel(name)
			},
			grid,
			xAxis: {
				type: 'value',
				show: false
			},
			yAxis: {
				type: 'category',
				name: '',
				data: names.map(truncateString(20)),
				axisTick: {
					show: false
				},
				axisLine: {
					show: false
				}
			},
			series,
			tooltip: {
				trigger: 'axis',
				axisPointer: {
					type: 'shadow'
				},
				formatter: (params) => {
					// Find the index of the hovered item and show full name
					const index = params[0].dataIndex;
					return names[index];
				}
			}
		};

		chart.setOption(option);

		window.addEventListener('resize', function () {
			chart.resize();
		});
	});
</script>

{#if data.length > 0}
	<div id={chart_id} class="{width} {height} {classesContainer}"></div>
{:else}
	<div class="flex justify-center items-center h-full">
		<div class="font-semibold">
			{m.nothingToShowYet()}
		</div>
	</div>
{/if}
