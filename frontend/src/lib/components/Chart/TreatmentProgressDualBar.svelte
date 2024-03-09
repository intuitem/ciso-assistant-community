<script lang="ts">
	import { onMount } from 'svelte';
	import * as m from '$paraglide/messages.js';

	export let agg_data = []; // Set this type later

	onMount(async () => {
		const echarts = await import('echarts');
		let element = document.getElementById('progress_div');
		let progress_ch = echarts.init(element, null, {
			renderer: 'svg'
		});

		let risk_open = m.riskOpen();
		let risk_mitigate = m.riskMitigate();
		let risk_accept = m.riskAccept();
		let risk_avoid = m.riskAvoid();
		let measure_open = m.measureOpen();
		let measure_progress = m.measureProgress();
		let measure_hold = m.measureHold();
		let measure_done = m.measureDone();

		// specify chart configuration item and data
		let option = {
			aria: {
				enabled: true,
				decal: {
					show: true
				}
			},
			toolbox: {
				show: true,
				feature: {
					mark: { show: true },
					dataView: { show: false, readOnly: true },
					saveAsImage: { show: true }
				}
			},
			tooltip: {
				trigger: 'axis',
				axisPointer: {
					type: 'shadow' // 默认为直线，可选为：'line' | 'shadow'
				}
			},
			legend: {
				data: [
					{ name: risk_open, itemStyle: { color: '#fac858' } },
					{ name: risk_mitigate, itemStyle: { color: '#91cc75' } },
					{ name: risk_accept, itemStyle: { color: '#73c0de' } },
					{ name: risk_avoid, itemStyle: { color: '#ee6666' } },
					{ name: measure_open, itemStyle: { color: '#fac858' } },
					{ name: measure_progress, itemStyle: { color: '#5470c6' } },
					{ name: measure_hold, itemStyle: { color: '#ee6666' } },
					{ name: measure_done, itemStyle: { color: '#91cc75' } }
				],
				show: true
			},
			grid: {
				left: '3%',
				right: '4%',
				bottom: '3%',
				containLabel: true
			},
			xAxis: [
				{
					axisTick: {
						alignWithLabel: true
					},
					axisLabel: {
						width: 80,
						interval: 0,
						overflow: 'break'
					},
					type: 'category',
					data: agg_data.names
				}
			],
			yAxis: [
				{
					type: 'value',
					minInterval: 1,
					show: false
				}
			],
			series: [
				{
					name: risk_open,
					type: 'bar',
					stack: 'risks',
					emphasis: {
						focus: 'series'
					},
					data: agg_data.rsk_status_out.open
				},
				{
					name: risk_mitigate,
					type: 'bar',
					stack: 'risks',
					emphasis: {
						focus: 'series'
					},
					data: agg_data.rsk_status_out.mitigate
				},
				{
					name: risk_accept,
					type: 'bar',
					stack: 'risks',
					emphasis: {
						focus: 'series'
					},
					data: agg_data.rsk_status_out.accept
				},
				{
					name: risk_avoid,
					type: 'bar',
					stack: 'risks',
					emphasis: {
						focus: 'series'
					},
					data: agg_data.rsk_status_out.avoid
				},
				{
					name: measure_open,
					type: 'bar',
					barWidth: 20,
					stack: 'applied_controls',
					emphasis: {
						focus: 'series'
					},
					data: agg_data.mtg_status_out.open
				},
				{
					name: measure_progress,
					type: 'bar',
					barWidth: 20,
					stack: 'applied_controls',
					emphasis: {
						focus: 'series'
					},
					data: agg_data.mtg_status_out.in_progress
				},
				{
					name: measure_hold,
					type: 'bar',
					barWidth: 20,
					stack: 'applied_controls',
					emphasis: {
						focus: 'series'
					},
					data: agg_data.mtg_status_out.on_hold
				},
				{
					name: measure_done,
					type: 'bar',
					barWidth: 20,
					stack: 'applied_controls',
					emphasis: {
						focus: 'series'
					},
					data: agg_data.mtg_status_out.done
				}
			]
		};
		// use configuration item and data specified to show chart
		progress_ch.setOption(option);
		progress_ch.resize();

		window.addEventListener('resize', function () {
			progress_ch.resize();
		});
	});
</script>

<div id="progress_div" class="bg-white w-auto h-[600px]" />
