<script lang="ts">
	import type { PageData } from './$types';
	import * as m from '$paraglide/messages';
	export let data: PageData;
	import TreeChart from '$lib/components/Chart/TreeChart.svelte';
	import TreemapChart from '$lib/components/Chart/TreemapChart.svelte';
</script>

<div class="card bg-white p-6 shadow flex flex-col space-y-4 w-screen">
	<div class="w-5/6 h-96">
		<TreeChart title="Organisation overview" tree={data.data} name="org_tree" />
	</div>
</div>
