<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<DetailView {data}>
	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4 bg-slate-100 rounded-xl p-4">
			<!-- LEC Chart Placeholder -->
			<div class="bg-white rounded-lg p-8 shadow-sm text-center">
				<div class="flex flex-col items-center space-y-4">
					<i class="fa-solid fa-chart-area text-4xl text-gray-400"></i>
					<h5 class="text-lg font-semibold text-gray-600">Loss Exceedance Curve (LEC)</h5>
					<p class="text-gray-500">
						Interactive chart showing the probability of losses exceeding specific thresholds
					</p>
					<div class="mt-4 px-4 py-2 bg-blue-100 text-blue-800 rounded-md">
						LEC Chart - Implementation pending
					</div>
				</div>
			</div>
		</div>
	{/snippet}
</DetailView>
