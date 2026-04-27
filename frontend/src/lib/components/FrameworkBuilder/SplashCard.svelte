<script lang="ts">
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';

	interface Props {
		name?: string | null;
		description?: string | null;
		id?: string | null;
		/** Extra classes appended to the outer wrapper div */
		class?: string;
	}

	let { name = null, description = null, id = null, class: className = '' }: Props = $props();
</script>

<div
	class="border-l-4 border-purple-400 rounded-xl shadow-sm bg-white overflow-hidden {className}"
	id={id ?? undefined}
>
	{#if name}
		<div class="px-6 py-4 border-b border-purple-100 flex items-center gap-2">
			<i class="fa-solid fa-display text-purple-400"></i>
			<span class="text-lg font-semibold text-gray-800">{name}</span>
		</div>
	{/if}
	{#if description}
		<div class="px-6 py-5">
			<MarkdownRenderer content={description} />
		</div>
	{/if}
</div>
