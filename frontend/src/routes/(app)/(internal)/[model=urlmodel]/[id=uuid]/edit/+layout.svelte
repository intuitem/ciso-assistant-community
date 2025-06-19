<script lang="ts">
	interface Props {
		children?: import('svelte').Snippet;
	}

	let { children }: Props = $props();
</script>

<div class="card p-4 bg-white shadow-lg">
	{@render children?.()}
</div>
