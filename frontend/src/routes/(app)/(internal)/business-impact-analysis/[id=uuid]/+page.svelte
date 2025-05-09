<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	export let data: PageData;
	import { m } from '$paraglide/messages';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { page } from '$app/stores';
	import ActivityTracker from '$lib/components/DataViz/ActivityTracker.svelte';
</script>

<DetailView {data}>
	<div slot="actions" class="flex flex-col space-y-2">
		<Anchor
			href={`${$page.url.pathname}/visual`}
			class="btn variant-filled-primary h-fit"
			breadcrumbAction="push"><i class="fa-solid fa-stopwatch mr-2"></i>{m.impactOverTime()}</Anchor
		>
	</div>
	<div slot="widgets" class="h-full flex flex-col space-y-4">
		<div class="card p-4 bg-gray-50 shadow-sm flex-grow">
			<div class="font-bold text-xl mb-4 capitalize">{m.recoveryInsights()}</div>
			<div class="flex items-center justify-center">
				<ActivityTracker metrics={data.metrics} />
			</div>
		</div>
	</div>
</DetailView>
