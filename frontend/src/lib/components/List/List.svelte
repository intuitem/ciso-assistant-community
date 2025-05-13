<script lang="ts">
	import List from '$lib/components/List/List.svelte';
	type NestedArray<T> = Array<T | NestedArray<T>>;
	interface Props {
		items: NestedArray<Record<string, string> | string>;
		message?: string;
		classesMessage?: string;
		[key: string]: any
	}

	let { items, message = '', classesMessage = 'bg-surface-100 bg-opacity-80 backdrop-blur-sm', ...rest }: Props = $props();
</script>

<article {...rest}>
	{#if message}
		<p class="sticky top-0 p-2 {classesMessage}">{message}</p>
	{/if}
	<ul class="list-disc ml-8 mr-4">
		{#each items as item}
			{#if item instanceof Array}
				<li>
					<List items={item} />
				</li>
			{:else if typeof item === 'object' && Object.hasOwn(item, 'str')}
				<li>{item.str}</li>
			{:else}
				<li>{item}</li>
			{/if}
		{/each}
	</ul>
</article>
