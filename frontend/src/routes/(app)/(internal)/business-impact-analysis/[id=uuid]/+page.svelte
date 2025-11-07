<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { page } from '$app/state';
	import ActivityTracker from '$lib/components/DataViz/ActivityTracker.svelte';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<DetailView {data}>
	{#snippet actions()}
		<div class="flex flex-col space-y-2">
			<Anchor
				href={`${page.url.pathname}/visual`}
				class="btn preset-filled-primary-500 h-fit"
				breadcrumbAction="push"
				><i class="fa-solid fa-stopwatch mr-2"></i>{m.impactOverTime()}</Anchor
			>
			<Anchor
				href={`${page.url.pathname}/report`}
				class="btn preset-filled-primary-500 h-fit"
				breadcrumbAction="push"><i class="fa-solid fa-file-lines mr-2"></i>{m.report()}</Anchor
			>
		</div>
	{/snippet}
	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4">
			<div class="card p-4 bg-gray-50 shadow-xs grow">
				<div class="font-bold text-xl mb-4">{m.recoveryInsights()}</div>
				<div class="flex items-center justify-center">
					<ActivityTracker metrics={data.metrics} />
				</div>
			</div>
		</div>
	{/snippet}
</DetailView>
