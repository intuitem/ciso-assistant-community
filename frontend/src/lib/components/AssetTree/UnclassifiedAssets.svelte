<script lang="ts">
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { m } from '$paraglide/messages';

	interface Props {
		count: number;
	}

	let { count }: Props = $props();

	const PAGE_SIZE = 20;

	type AssetRow = { id: string; name: string; folder?: { str?: string } };

	let isExpanded = $state(false);
	let assets = $state<AssetRow[]>([]);
	let loaded = $state(0);
	let total = $state(count);
	let isLoading = $state(false);

	async function loadAssets() {
		if (isLoading) return;
		isLoading = true;
		try {
			const res = await fetch(
				`/assets?asset_class__isnull=true&limit=${PAGE_SIZE}&offset=${loaded}`
			);
			if (res.ok) {
				const data = await res.json();
				assets = [...assets, ...(data.results ?? [])];
				loaded = assets.length;
				total = data.count ?? loaded;
			}
		} catch (e) {
			console.error('UnclassifiedAssets: failed to fetch assets', e);
		} finally {
			isLoading = false;
		}
	}

	function toggle() {
		isExpanded = !isExpanded;
		if (isExpanded && assets.length === 0) loadAssets();
	}
</script>

<li class="list-none m-0 p-0 border-t border-surface-200-800 mt-2 pt-2">
	<button
		type="button"
		onclick={toggle}
		class="flex items-center gap-2 w-full px-2 py-1.5 rounded text-left text-sm hover:bg-surface-100-900 transition-colors"
		aria-expanded={isExpanded}
	>
		<i
			class="fa-solid fa-chevron-right text-[9px] text-surface-500 transition-transform duration-150 {isExpanded
				? 'rotate-90'
				: ''}"
		></i>
		<i class="fa-solid fa-circle-question text-xs text-surface-400"></i>
		<span class="truncate italic text-surface-600-400">{m.unclassifiedAssets()}</span>
		<span class="badge preset-tonal-surface text-xs shrink-0">{count}</span>
	</button>

	{#if isExpanded}
		<ul class="list-none m-0 p-0 pl-8">
			{#each assets as asset (asset.id)}
				<li class="list-none">
					<Anchor
						breadcrumbAction="push"
						href="/assets/{asset.id}"
						class="flex items-center gap-2 px-2 py-1 rounded text-sm hover:bg-surface-100-900 anchor"
					>
						<i class="fa-solid fa-cube text-[10px] text-surface-400"></i>
						<span class="truncate">{asset.name}</span>
						{#if asset.folder?.str}
							<span class="text-[10px] text-surface-500">{asset.folder.str}</span>
						{/if}
					</Anchor>
				</li>
			{/each}
			{#if isLoading}
				<li class="px-2 py-1 text-xs text-surface-500 list-none">
					<i class="fa-solid fa-spinner animate-spin"></i>
				</li>
			{:else if loaded < total}
				<li class="list-none">
					<button
						type="button"
						onclick={loadAssets}
						class="px-2 py-1 text-xs text-primary-600 hover:underline"
					>
						{m.loadMoreAssets()} ({loaded}/{total})
					</button>
				</li>
			{/if}
		</ul>
	{/if}
</li>
