<script lang="ts">
	import ImpactEffortMatrix from './ImpactEffortMatrix.svelte';
	import type { PageData } from './$types';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<ImpactEffortMatrix data={data.data} />
