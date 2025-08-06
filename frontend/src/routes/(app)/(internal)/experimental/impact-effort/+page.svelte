<script lang="ts">
	import ImpactEffortMatrix from './ImpactEffortMatrix.svelte';
	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();
</script>

<ImpactEffortMatrix data={data.data} />
