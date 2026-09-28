<script lang="ts">
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	interface Props {
		cell: any;
		meta?: any;
	}

	let { cell, meta }: Props = $props();

	// The register spans models, so the link target varies per row: a single
	// `foreignKeyFields` entry cannot express it.
	const URL_MODEL_BY_TYPE: Record<string, string> = {
		appliedcontrol: 'applied-controls',
		tasktemplate: 'task-templates'
	};

	const href = $derived(
		cell?.id && URL_MODEL_BY_TYPE[meta?.target_type]
			? `/${URL_MODEL_BY_TYPE[meta.target_type]}/${cell.id}`
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
