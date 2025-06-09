<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { page } from '$app/stores';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	export let data: PageData;
	import HalfDonutChart from '$lib/components/Chart/HalfDonutChart.svelte';
	import DonutChart from '$lib/components/Chart/DonutChart.svelte';
</script>

<DetailView {data}>
	<div slot="actions" class="flex flex-col space-y-2">
		<Anchor
			href={`${$page.url.pathname}/action-plan`}
			class="btn variant-filled-primary h-fit"
			breadcrumbAction="push"><i class="fa-solid fa-heart-pulse mr-2" />Advanced analytics</Anchor
		>
	</div>

	<div slot="widgets" class="h-full flex flex-col space-y-4"></div>
</DetailView>
