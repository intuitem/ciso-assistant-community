<script lang="ts">
	import ImpactEffortMatrix from './ImpactEffortMatrix.svelte';
	import ImpactEffortMatrix2 from './ImpactEffortMatrix2.svelte';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<ImpactEffortMatrix2 data={data} showGrid={false} />
