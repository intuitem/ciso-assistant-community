<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import HalfDonutChart from '$lib/components/Chart/HalfDonutChart.svelte';
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	$inspect(data);
</script>

<DetailView {data}>
	{#snippet actions()}
		<div class="flex flex-col space-y-2">
			<Anchor
				href={`${page.url.pathname}/run-simulation`}
				class="btn bg-pink-500 text-white h-fit"
				breadcrumbAction="push"><i class="fa-solid fa-play mr-2"></i>Run simulation</Anchor
			>
		</div>
	{/snippet}

	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4 bg-slate-100 rounded-xl">
			{JSON.stringify(data.lec, null, 4)}
		</div>
	{/snippet}
</DetailView>
