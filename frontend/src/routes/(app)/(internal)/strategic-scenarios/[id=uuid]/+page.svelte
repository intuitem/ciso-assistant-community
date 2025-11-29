<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<DetailView {data}>
	{#snippet widgets()}
		<div class="h-full flex flex-col space-y-4">
			<div class="card p-4 bg-gray-50 shadow-xs grow">
				<h3 class="text-lg font-semibold mb-4">
					<i class="fa-solid fa-chart-line mr-2"></i>
					{m.strategicScenario()} Analytics
				</h3>
				<p class="text-sm text-gray-500">Widget section - Coming soon</p>
			</div>
		</div>
	{/snippet}
</DetailView>
