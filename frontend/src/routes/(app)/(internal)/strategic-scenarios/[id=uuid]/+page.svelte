<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import AttackPathGraph from '$lib/components/EbiosRM/AttackPathGraph.svelte';
	import AttackPathFlowText from '$lib/components/EbiosRM/AttackPathFlowText.svelte';
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
					<i class="fa-solid fa-route mr-2"></i>
					{m.attackPaths()}
				</h3>
				{#key data.attackPaths}
					{#if data.attackPaths && data.attackPaths.length > 0}
						<!-- Graph visualization -->
						<AttackPathGraph
							attackPaths={data.attackPaths}
							fearedEvents={data.fearedEventsWithAssets || []}
							height="700px"
						/>
					{:else}
						<div class="flex flex-col items-center justify-center py-12 text-center">
							<i class="fa-solid fa-diagram-project text-gray-300 text-6xl mb-4"></i>
							<p class="text-gray-500 text-sm">{m.noAttackPathsDefined()}</p>
							<p class="text-gray-400 text-xs mt-2">
								Add attack paths to visualize the strategic scenario
							</p>
						</div>
					{/if}
				{/key}
			</div>
		</div>
	{/snippet}
</DetailView>
