<script lang="ts">
	import type { PageData } from './$types';
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	export let data: PageData;
	import LineHeatmap from '$lib/components/DataViz/LineHeatmap.svelte';
	import { m } from '$paraglide/messages';
</script>

<DetailView {data}>
	<div slot="widgets" class="h-full flex flex-col space-y-4">
		<div class="card p-4 bg-gray-50 shadow-sm flex-grow">
			<div class="grid grid-cols-2">
				<div class="w-1/2">
					<div class="font-serif font-bold mb-2 capitalize">
						<i class="fa-solid fa-bullseye mr-2"></i>{m.recoveryIndicators()}
					</div>
					{#each data.asset.disaster_recovery_objectives as objective}
						<div class="uppercase">{objective.str}</div>
					{/each}
				</div>
				<div class="w-1/2">
					<div class="font-serif font-bold mb-2 capitalize">
						<i class="fa-solid fa-shield-halved mr-2"></i>
						{m.securityObjectives()}
					</div>
					{#each data.asset.security_objectives as objective}
						<div class="capitalize">{objective.str}</div>
					{/each}
				</div>
			</div>
			<div class="font-serif font-bold mt-4 mb-2">
				<i class="fa-solid fa-chart-line mr-2"></i>{m.impactOverTime()}
			</div>
			<LineHeatmap data={data.aaMetrics} />
		</div>
	</div>
</DetailView>
