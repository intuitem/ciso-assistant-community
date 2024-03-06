<script lang="ts">
	import { TreeView, TreeViewItem } from '@skeletonlabs/skeleton';

	export let header: string;
	export let open = false;
	export let icon: string;
	export let style: string;
</script>

<TreeView hover={style} caretClosed="-rotate-90" caretOpen="">
	{#if icon}
		<TreeViewItem {open}>
			<svelte:fragment slot="lead"><i class={icon} /></svelte:fragment>
			<p class="font-medium">{header}</p>
			<svelte:fragment slot="children">
				<slot />
			</svelte:fragment>
		</TreeViewItem>
	{:else}
		<TreeViewItem {open}>
			<p class="font-medium">{header}</p>
			<svelte:fragment slot="children">
				<slot />
			</svelte:fragment>
		</TreeViewItem>
	{/if}
</TreeView>
