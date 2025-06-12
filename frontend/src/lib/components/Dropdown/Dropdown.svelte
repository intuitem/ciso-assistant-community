<script lang="ts">
	import { Accordion } from '@skeletonlabs/skeleton-svelte';

	interface Props {
		header: string;
		open?: boolean;
		icon: string;
		style: string;
		children?: import('svelte').Snippet;
	}

	let { header, open = false, icon, style, children }: Props = $props();
	let value = $derived([open.toString()]);
</script>

<Accordion {value} onValueChange={(e) => (value = e.value)} collapsible>
	<Accordion.Item value="true">
		{#snippet lead()}
			<i class={icon}></i>
		{/snippet}
		{#snippet control()}
			<p class="font-medium">{header}</p>
		{/snippet}
		{#snippet panel()}
			{@render children?.()}
		{/snippet}
	</Accordion.Item>
</Accordion>
