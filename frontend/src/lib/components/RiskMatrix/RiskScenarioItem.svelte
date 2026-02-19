<script lang="ts">
	interface Props {
		data: any;
	}

	let { data }: Props = $props();
</script>

<p class="whitespace-nowrap text-surface-900">
	{#if data.strength_of_knowledge && data.strength_of_knowledge.symbol !== undefined}
		<span class="font-mono text-lg">{data.strength_of_knowledge.symbol}</span>
	{/if}
	<span>{data.ref_id}</span>
</p>
