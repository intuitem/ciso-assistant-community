<script lang="ts">
	import AssetClassNode, { type ClassNode } from '$lib/components/AssetTree/AssetClassNode.svelte';
	import UnclassifiedAssets from '$lib/components/AssetTree/UnclassifiedAssets.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let hideEmpty = $state(true);

	const tree = $derived((data.classTree?.tree ?? []) as ClassNode[]);
	const visibleRoots = $derived(tree.filter((n) => !hideEmpty || n.total_count > 0));
	const unclassifiedCount = $derived(data.classTree?.unclassified_count ?? 0);
	const totalCount = $derived(data.classTree?.total_count ?? 0);
</script>

<div class="flex flex-col space-y-4">
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-3">
			<Anchor
				href="/assets"
				class="btn-mini-secondary rounded w-9 h-9 shrink-0 inline-flex items-center justify-center"
				label={m.assets()}
				title={m.assets()}><i class="fa-solid fa-arrow-left"></i></Anchor
			>
			<span class="text-sm text-surface-600-400">
				{totalCount}
				{m.assets().toLowerCase()}
			</span>
		</div>
		<label class="flex items-center gap-2 text-sm">
			<input type="checkbox" class="checkbox" bind:checked={hideEmpty} />
			<span>{m.hideEmptyClasses()}</span>
		</label>
	</div>

	<div class="card bg-surface-50-950 p-4">
		{#if visibleRoots.length === 0 && unclassifiedCount === 0}
			<p class="text-sm text-surface-500 text-center py-6">{m.noResultFound()}</p>
		{:else}
			<ul class="list-none m-0 p-0">
				{#each visibleRoots as node (node.id)}
					<AssetClassNode {node} {hideEmpty} />
				{/each}
				{#if unclassifiedCount > 0}
					<UnclassifiedAssets count={unclassifiedCount} />
				{/if}
			</ul>
		{/if}
	</div>
</div>
