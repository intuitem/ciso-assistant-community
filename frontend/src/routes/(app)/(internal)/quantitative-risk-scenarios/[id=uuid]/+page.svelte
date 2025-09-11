<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { onMount } from 'svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	onMount(async () => {
		if (data.lec?.curves?.length > 0) {
      //temporary embedded chart for now
			const echarts = await import('echarts');
			const chart = echarts.init(document.getElementById('combined-lec-chart'));

			const series = data.lec.curves.map((curve: any, index: number) => {
				return {
					name: curve.name,
					type: 'line',
					data: curve.data,
					smooth: true,
					symbol: 'none',
					lineStyle: {
						width: 3
					}
				};
			});

			const currency = data.lec.currency || '$';
			const option = {
				legend: {
					top: 0,
					data: data.lec.curves.map((curve: any) => ({
						name: curve.name,
						icon: 'circle'
					}))
				},
				grid: {
					left: '10%',
					right: '10%',
					top: '15%',
					bottom: '15%'
				},
				xAxis: {
					type: 'log',
					name: `Loss Amount (${currency})`,
					nameLocation: 'middle',
					nameGap: 30,
					axisLabel: {
						formatter: (value: number) => {
							if (value >= 1000000) return currency + (value/1000000).toFixed(0) + 'M';
							if (value >= 1000) return currency + (value/1000).toFixed(0) + 'K';
							return currency + value.toFixed(0);
						}
					}
				},
				yAxis: {
					type: 'value',
					name: 'Exceedance Probability',
					nameLocation: 'middle',
					nameGap: 50,
					axisLabel: {
						formatter: (value: number) => (value * 100).toFixed(0) + '%'
					}
				},
				series: series
			};

			chart.setOption(option);

			window.addEventListener('resize', () => chart.resize());
		}
	});

	$inspect(data);
</script>

<DetailView {data}>
	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4 bg-slate-100 rounded-xl p-4">
			{#if data.lec?.curves?.length > 0}
				<!-- Multi-Curve LEC Chart -->
				<div class="bg-white rounded-lg p-4 shadow-sm w-full">
					<h5 class="text-lg font-semibold text-gray-700 mb-4">Combined hypotheses</h5>
					<div id="combined-lec-chart" style="height: 400px; width: 100%;"></div>
				</div>
			{:else}
				<!-- Empty State -->
				<div class="bg-white rounded-lg p-8 shadow-sm text-center">
					<div class="flex flex-col items-center space-y-4">
						<i class="fa-solid fa-chart-area text-4xl text-gray-400"></i>
						<h5 class="text-lg font-semibold text-gray-600">Loss Exceedance Curves</h5>
						<p class="text-gray-500">
							No curve data available. Run simulations on your hypotheses to generate LEC charts.
						</p>
					</div>
				</div>
			{/if}
		</div>
	{/snippet}
</DetailView>
