<script lang="ts">
	import { page } from '$app/state';
	let { children } = $props();
</script>

<!-- The requirement pages seed script values, tab state and their tables from
     `data` once. Same-route navigation to another requirement (e.g. a mapped
     requirement's link) reuses the component, leaving the previous requirement
     on screen — key the whole subtree on the id so it remounts instead. -->
{#key page.params.id}
	{@render children()}
{/key}
