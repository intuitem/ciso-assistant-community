<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { page } from '$app/stores';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import RingProgress from '$lib/components/DataViz/RingProgress.svelte';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<DetailView {data}>
	{#snippet actions()}
		<div class="flex flex-col space-y-2">
			<!-- <Anchor -->
			<!-- 	href={`${$page.url.pathname}/action-plan`} -->
			<!-- 	class="btn variant-filled-primary h-fit" -->
			<!-- 	breadcrumbAction="push" -->
			<!-- > -->
			<!-- 	<i class="fa-solid fa-heart-pulse mr-2" />Advanced analytics -->
			<!-- </Anchor> -->
		</div>
	{/snippet}
	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-6 p-4">
			<div class="grid grid-cols-3 gap-4">
				<div class="bg-white rounded-lg shadow-sm border p-6 col-span-2">
					<div class="flex flex-col items-center">
						<h3 class="text-lg font-semibold text-gray-800 mb-4">
							{m.averageProgress()}
						</h3>
						<RingProgress
							value={data.metrics.avg_progress}
							max={100}
							isPercentage={true}
							classesContainer="w-32 h-32"
						/>
					</div>
				</div>
				<div class="bg-white rounded-lg shadow-sm border p-6 flex items-center justify-center">
					<div class="flex flex-col items-center text-center">
						<div class="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-3">
							<i class="fa-solid fa-calendar-days text-blue-600 text-xl"></i>
						</div>
						<h3 class="text-lg font-semibold text-gray-800 mb-2">
							{m.daysRemaining()}
						</h3>
						<p class="text-3xl font-bold text-gray-900">
							{data.metrics.days_remaining}
							<span class="text-sm font-normal text-gray-500 ml-1">{m.days()}</span>
						</p>
					</div>
				</div>
			</div>
		</div>
	{/snippet}
</DetailView>
