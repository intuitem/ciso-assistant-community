<script lang="ts">
	interface Props {
		data: { title: string; description?: string; html: string };
	}

	let { data }: Props = $props();
</script>

<svelte:head>
	<title>{data.title} | CISO TSI</title>
</svelte:head>

<article class="prose dark:prose-invert max-w-3xl">
	<h1>{data.title}</h1>
	{#if data.description}
		<p class="text-surface-600-400 -mt-4">{data.description}</p>
	{/if}
	{@html data.html}
</article>
