<script lang="ts">
	import { page } from '$app/state';
	import type { Snippet } from 'svelte';

	// Renders an implementation score and a documentation score (rings, inputs,
	// badges...) in the order set in the general settings: implementation first
	// unless "documentation_score_first" is on, as in the CCB CyFun tools. Each
	// snippet is told whether it comes first (e.g. to carry the scoring switch).
	// No wrapper element, so the parent layout is unchanged.
	interface Props {
		implementation?: Snippet<[boolean]>;
		documentation?: Snippet<[boolean]>;
	}

	let { implementation, documentation }: Props = $props();

	const documentationFirst = $derived(Boolean(page.data.settings?.documentation_score_first));
</script>

{#if documentationFirst}
	{@render documentation?.(true)}
	{@render implementation?.(false)}
{:else}
	{@render implementation?.(true)}
	{@render documentation?.(false)}
{/if}
