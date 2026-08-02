<script lang="ts">
	interface Props {
		cell: any;
		meta?: any;
	}

	let { cell }: Props = $props();
</script>

{#if cell}
	<span class="inline-block max-w-64 truncate align-middle" title={cell}>{cell}</span>
{/if}
