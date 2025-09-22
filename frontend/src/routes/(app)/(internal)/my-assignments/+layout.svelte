<script lang="ts">
	interface Props {
		children?: import('svelte').Snippet;
	}

	let { children }: Props = $props();
</script>

<div class="card bg-white shadow-lg">
	{@render children?.()}
</div>
