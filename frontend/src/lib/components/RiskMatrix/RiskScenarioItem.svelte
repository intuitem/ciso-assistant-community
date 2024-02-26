<script lang="ts">
	export let data: any;
</script>

<p class="whitespace-nowrap">
	{data.rid}
	{#if data.strength_of_knowledge && data.strength_of_knowledge.symbol !== undefined}
		<sub>{data.strength_of_knowledge.symbol}</sub>
	{/if}
</p>
