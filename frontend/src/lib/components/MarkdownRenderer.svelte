<script lang="ts">
	import { marked } from 'marked';

	interface Props {
		content: string | null | undefined;
		class?: string;
	}

	let { content, class: className = '' }: Props = $props();

	let renderedContent = $derived(
		content && content.trim() !== '' ? (marked(content) as string) : ''
	);
</script>

{#if renderedContent}
	<div class="prose prose-sm max-w-none {className}">
		{@html renderedContent}
	</div>
{:else}
	<span class="text-gray-500 italic">--</span>
{/if}
