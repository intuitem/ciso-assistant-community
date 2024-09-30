<script lang="ts">
	import List from '$lib/components/List/List.svelte';
	type NestedArray<T> = Array<T | NestedArray<T>>;
	export let items: NestedArray<Record<string, string> | string>;
	export let message: string = '';
	export let classesMessage: string = 'bg-surface-100 bg-opacity-80 backdrop-blur-sm';
</script>

<article {...$$restProps}>
	{#if message}
		<p class="sticky top-0 p-2 {classesMessage}">{message}</p>
	{/if}
	<ul class="list-disc ml-8 mr-4">
		{#each items as item}
			{#if item instanceof Array}
				<li>
					<svelte:component this={List} items={item} />
				</li>
			{:else if typeof item === 'object' && Object.hasOwn(item, 'str')}
				<li>{item.str}</li>
			{:else}
				<li>{item}</li>
			{/if}
		{/each}
	</ul>
</article>
