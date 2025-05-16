<script lang="ts">
	// import { TreeView, TreeViewItem } from '@skeletonlabs/skeleton';

	interface Props {
		header: string;
		open?: boolean;
		icon: string;
		style: string;
		children?: import('svelte').Snippet;
	}

	let { header, open = false, icon, style, children }: Props = $props();
</script>

<!-- <TreeView hover={style} caretClosed="-rotate-90" caretOpen=""> -->
<!-- 	{#if icon} -->
<!-- 		<TreeViewItem {open}> -->
<!-- 			{#snippet lead()} -->
<!-- 						<i class={icon}></i> -->
<!-- 					{/snippet} -->
<!-- 			<p class="font-medium">{header}</p> -->
<!-- 			{#snippet children()} -->
<!---->
<!-- 					{@render children?.()} -->
<!---->
<!-- 					{/snippet} -->
<!-- 		</TreeViewItem> -->
<!-- 	{:else} -->
<!-- 		<TreeViewItem {open}> -->
<!-- 			<p class="font-medium">{header}</p> -->
<!-- 			{#snippet children()} -->
<!---->
<!-- 					{@render children?.()} -->
<!---->
<!-- 					{/snippet} -->
<!-- 		</TreeViewItem> -->
<!-- 	{/if} -->
<!-- </TreeView> -->
