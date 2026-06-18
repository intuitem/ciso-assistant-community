<script lang="ts">
	interface Props {
		children?: import('svelte').Snippet;
	}

	let { children }: Props = $props();
</script>

<div class="card p-4 bg-surface-50-950 shadow-lg">
	{@render children?.()}
</div>
