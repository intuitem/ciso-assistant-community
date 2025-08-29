<script lang="ts">
	import type { ActionData, PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import HalfDonutChart from '$lib/components/Chart/HalfDonutChart.svelte';
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	import LossExceedanceCurve from '$lib/components/Chart/LossExceedanceCurve.svelte';
	import { ProgressRing } from '@skeletonlabs/skeleton-svelte';
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { run } from 'svelte/legacy';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
	let simulationIsLoading = $state(false);

	// Calculate min and max values for the LEC chart from the data
	const lecMinValue = $derived(() => {
		if (!data.lec?.data || !Array.isArray(data.lec.data) || data.lec.data.length === 0) {
			return undefined;
		}
		const minFromData = Math.min(...data.lec.data.map(([x, _]: [number, number]) => x));
		return Math.max(minFromData * 0.8, 1); // Reduce by 20% but minimum of $1
	});

	const lecMaxValue = $derived(() => {
		if (!data.lec?.data || !Array.isArray(data.lec.data) || data.lec.data.length === 0) {
			return 1000000; // Default max value
		}
		const maxFromData = Math.max(...data.lec.data.map(([x, _]: [number, number]) => x));
		return Math.ceil(maxFromData * 1.2); // Add 20% padding
	});

	$inspect(data);
	$inspect('LEC data:', data.lec);

	run(() => {
		if (form?.message?.simulationComplete) {
			invalidateAll();
		}
	});
</script>

<DetailView {data}>
	{#snippet actions()}
		<div class="flex flex-col space-y-2">
			<form
				method="POST"
				action="?/runSimulation"
				use:enhance={() => {
					simulationIsLoading = true;
					return async ({ update }) => {
						await update();
						simulationIsLoading = false;
					};
				}}
			>
				<button
					type="submit"
					class="btn bg-pink-500 text-white h-fit"
					disabled={simulationIsLoading}
				>
					<span class="mr-2">
						{#if simulationIsLoading}
							<ProgressRing
								strokeWidth="16px"
								meterStroke="stroke-white"
								size="size-6"
								classes="-ml-2"
							/>
						{:else}
							<i class="fa-solid fa-play"></i>
						{/if}
					</span>
					Run simulation
				</button>
			</form>
		</div>
	{/snippet}

	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4 bg-slate-100 rounded-xl p-4">
			{#if data.lec?.data && Array.isArray(data.lec.data) && data.lec.data.length > 0}
				<!-- LEC Chart -->
				<div class="bg-white rounded-lg p-4 shadow-sm w-full">
					{#key data.lec.simulation_timestamp}
						<LossExceedanceCurve
							data={data.lec.data}
							xMin={lecMinValue()}
							xMax={lecMaxValue()}
							height="h-96"
							width="w-full"
							classesContainer="min-w-0"
							enableTooltip={true}
							autoYMax={true}
						/>
					{/key}
				</div>

				<!-- Risk Metrics -->
				<div class="bg-white rounded-lg p-6 shadow-sm">
					<h3 class="text-lg font-semibold mb-4">Risk Insights</h3>
					{#if data.lec.metrics}
						<div class="grid grid-cols-2 md:grid-cols-4 gap-6">
							{#each Object.entries(data.lec.metrics) as [key, value]}
								<div class="text-center">
									<div class="text-2xl font-bold text-blue-600 mb-2">
										{#if typeof value === 'number'}
											{#if key.toLowerCase().includes('prob') && !key.startsWith('loss_with_')}
												{(value * 100).toFixed(2)}%
											{:else}
												{value >= 1000000 ? `$${Math.round(value / 1000000)}M` :
												 value >= 1000 ? `$${Math.round(value / 1000)}K` :
												 `$${Math.round(value).toLocaleString()}`}
											{/if}
										{:else}
											{value}
										{/if}
									</div>
									<div class="text-sm text-gray-600 capitalize leading-tight">
										{#if key.startsWith('loss_with_') && key.endsWith('_percent')}
											{@const percentage = key.replace('loss_with_', '').replace('_percent', '').replace('_', '.')}
											Loss with {percentage}% chance
										{:else}
											{key.replace(/_/g, ' ')}
										{/if}
									</div>
								</div>
							{/each}
						</div>
					{:else}
						<p class="text-gray-500">No metrics available</p>
					{/if}
				</div>
			{:else}
				<div class="bg-white rounded-lg p-8 text-center text-gray-500 shadow-sm">
					No LEC data available. Run a simulation to generate the chart.
				</div>
			{/if}
		</div>
	{/snippet}
</DetailView>
