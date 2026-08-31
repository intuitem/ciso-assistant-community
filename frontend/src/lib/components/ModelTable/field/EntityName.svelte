<script lang="ts">
	import { m } from '$paraglide/messages';
	interface Props {
		cell: string;
		[key: string]: any;
	}

	let { cell, ...rest }: Props = $props();

	let isMain = $derived(rest.meta?.is_main);
</script>

{cell}
{#if isMain}
	<i
		class="fa-solid fa-star text-primary-500 ml-1 text-xs align-middle"
		title={m.mainEntity()}
		data-testid="main-entity-badge"
	></i>
{/if}
