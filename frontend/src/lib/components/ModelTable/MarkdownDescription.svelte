<script lang="ts">
	import MarkdownRenderer from '../MarkdownRenderer.svelte';

	interface Props {
		cell: string;
	}

	let { cell }: Props = $props();
	export const meta: any = undefined;
</script>

<MarkdownRenderer content={cell} />
