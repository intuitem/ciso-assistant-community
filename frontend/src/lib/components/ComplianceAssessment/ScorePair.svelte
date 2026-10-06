<script lang="ts">
	import { page } from '$app/state';
	import type { Snippet } from 'svelte';

	// Renders an implementation score and a documentation score (rings, inputs,
	// badges...) in the order set in the general settings: implementation first
	// unless "documentation_score_first" is on, as in the CCB CyFun tools.
	// No wrapper element, so the parent layout is unchanged.
	interface Props {
		implementation?: Snippet;
		documentation?: Snippet;
	}

	let { implementation, documentation }: Props = $props();

	const documentationFirst = $derived(Boolean(page.data.settings?.documentation_score_first));
</script>

{#if documentationFirst}
	{@render documentation?.()}
	{@render implementation?.()}
{:else}
	{@render implementation?.()}
	{@render documentation?.()}
{/if}
