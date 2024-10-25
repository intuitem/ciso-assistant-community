<script lang="ts">
	import type { PageData } from './$types';
	export let data: PageData;
	import TreeChart from '$lib/components/Chart/TreeChart.svelte';
</script>

<div class="bg-white p-6 shadow flex overflow-x-auto">
	<div class="w-full h-96">
		<TreeChart title="Organisation overview" tree={data.data} name="org_tree" />
	</div>
</div>
