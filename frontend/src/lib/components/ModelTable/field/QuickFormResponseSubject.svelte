<script lang="ts">
	import { SUBJECT_ROUTES } from '#lib/utils/subject-routes.js';
	import Anchor from '#lib/components/Anchor/Anchor.svelte';

	interface Props {
		cell: any;
		meta?: any;
	}

	let { cell }: Props = $props();

	const href = $derived(
		cell?.id && SUBJECT_ROUTES[cell?.model]
			? `/${SUBJECT_ROUTES[cell.model]}/${cell.id}`
			: undefined
	);
</script>

{#if cell?.str}
	{#if href}
		<Anchor breadcrumbAction="push" {href} class="anchor" stopPropagation>{cell.str}</Anchor>
	{:else}
		{cell.str}
	{/if}
{:else}
	-
{/if}
