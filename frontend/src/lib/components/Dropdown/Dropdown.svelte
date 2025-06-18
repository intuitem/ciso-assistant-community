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
	{#snippet iconOpen()}
		<svg xmlns="http://www.w3.org/2000/svg" width="14px" height="14px" viewBox="0 0 448 512">
			<path
				d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
			/>
		</svg>
	{/snippet}
	{#snippet iconClosed()}
		<svg
			xmlns="http://www.w3.org/2000/svg"
			class="-rotate-90"
			width="14px"
			height="14px"
			viewBox="0 0 448 512"
		>
			<path
				d="M201.4 374.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 306.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"
			/>
		</svg>
	{/snippet}
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
