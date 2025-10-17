<script lang="ts">
	import type { PageData } from './$types';
	import { pageTitle } from '$lib/utils/stores';
	import TimelineTable from '$lib/components/BIA/TimelineTable.svelte';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
	pageTitle.set('Visual Analysis');
</script>

<TimelineTable data={data.data} />
