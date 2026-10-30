<script lang="ts">
	import { page } from '$app/state';

	interface Props {
		children?: import('svelte').Snippet;
	}

	let { children }: Props = $props();
</script>

<!-- The draft page and the hosted editors (framework, matrix, preset) seed
     page-script state from `data` once. Same-route navigation between two
     drafts (e.g. browser back/forward) reuses the component, leaving the
     editor working against the previous draft — key the whole subtree on the
     draft id so it remounts instead. -->
{#key page.params.id}
	{@render children?.()}
{/key}
