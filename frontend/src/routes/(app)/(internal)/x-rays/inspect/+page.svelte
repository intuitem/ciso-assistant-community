<script lang="ts">
	import type { PageData } from './$types';
	import TreeChart from '$lib/components/Chart/TreeChart.svelte';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<div class="bg-white p-6 shadow-sm flex overflow-x-auto">
	<div class="w-full h-dvh">
		<TreeChart title="Organisation overview" tree={data.data} name="org_tree" />
	</div>
</div>
