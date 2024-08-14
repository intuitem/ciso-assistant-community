<script lang="ts">
	export let data: any;
</script>

<p class="whitespace-nowrap">
	{#if data.strength_of_knowledge && data.strength_of_knowledge.symbol !== undefined}
		<sup class="font-mono text-lg">{data.strength_of_knowledge.symbol}</sup>
	{/if}
	<span>{data.rid}</span>
</p>
