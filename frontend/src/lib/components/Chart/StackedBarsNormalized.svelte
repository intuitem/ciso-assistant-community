<script lang="ts">
	import { onMount } from 'svelte';
	export let width = 'w-auto';
	export let height = 'h-full';
	export let classesContainer = '';
	export let data;
	export let names;
	export let uuids;
	import * as m from '$paraglide/messages';

	const chart_id = `stacked_div`;
	onMount(async () => {
		const echarts = await import('echarts');
		let chart = echarts.init(document.getElementById(chart_id), null, { renderer: 'svg' });
		const rawData = data;
		const auditTotals = rawData.map((audit) => audit.reduce((sum, val) => sum + val, 0));
		const uuidMap = uuids;
		chart.on('click', function (params) {
			if (uuidMap[params.name]) {
				window.open(`/compliance-assessments/${uuidMap[params.name]}`, '_blank');
				//window.location.href = `/compliance-assessments/${uuidMap[params.name]}`;
			}
		});
		const grid = {
			left: 150,
			right: 50,
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
			//color: ['#D2D5DB', '#FDE048', '#F87171', '#86EFAC', '#000'],
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
				data: names,
				axisTick: {
					show: false
				},
				axisLine: {
					show: false
				}
			},
			series
		};

		chart.setOption(option);

		window.addEventListener('resize', function () {
			chart.resize();
		});
	});
</script>

{#if data.length > 0}
	<div id={chart_id} class="{width} {height} {classesContainer}" />
{:else}
	<div class="flex justify-center items-center h-full">
		<div class="font-semibold">
			{m.nothingToShowYet()}
		</div>
	</div>
{/if}
