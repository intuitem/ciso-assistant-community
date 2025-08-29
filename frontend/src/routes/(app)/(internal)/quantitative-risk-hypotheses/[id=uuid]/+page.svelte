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

	// Calculate max value for the LEC chart from the data
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
				<LossExceedanceCurve
					data={data.lec.data}
					xMax={lecMaxValue()}
					height="h-96"
					width="w-full"
				/>
			{:else}
				<div class="text-center text-gray-500 py-8">
					No LEC data available. Run a simulation to generate the chart.
				</div>
			{/if}
		</div>
	{/snippet}
</DetailView>
