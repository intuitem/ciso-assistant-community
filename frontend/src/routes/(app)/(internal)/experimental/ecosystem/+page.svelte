<script lang="ts">
	import type { PageData } from './$types';
	import EcosystemRadarChart from '$lib/components/Chart/EcosystemRadarChart.svelte';
	import { m } from '$paraglide/messages';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="bg-white shadow flex overflow-x-auto">
	<div class="w-full h-screen">
		<EcosystemRadarChart title={m.current()} name="c_ecosystem" data={data.data.current} />
		<EcosystemRadarChart title={m.residual()} name="r_ecosystem" data={data.data.residual} />
	</div>
</div>
