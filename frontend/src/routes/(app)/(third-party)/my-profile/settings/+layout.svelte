<script lang="ts">
	interface Props {
		children?: import('svelte').Snippet;
	}

	let { children }: Props = $props();
</script>

<div class="card bg-surface-50-950 shadow-lg p-4">
	{@render children?.()}
</div>
