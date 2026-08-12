<script lang="ts">
	import AssetClassNode from './AssetClassNode.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { m } from '$paraglide/messages';

	export interface ClassNode {
		id: string;
		name: string;
		translated_name: string;
		builtin: boolean;
		is_visible: boolean;
		direct_count: number;
		total_count: number;
		children: ClassNode[];
	}

	interface Props {
		node: ClassNode;
		hideEmpty: boolean;
		depth?: number;
	}

	let { node, hideEmpty, depth = 0 }: Props = $props();

	const PAGE_SIZE = 20;

	type AssetRow = { id: string; name: string; folder?: { str?: string } };

	let isExpanded = $state(false);
	let assets = $state<AssetRow[]>([]);
	let loaded = $state(0);
	let total = $state(node.direct_count);
	let isLoading = $state(false);

	const visibleChildren = $derived(
		(node.children ?? []).filter((c) => !hideEmpty || c.total_count > 0)
	);
	const hasChildren = $derived(visibleChildren.length > 0);
	const label = $derived(
		node.builtin ? safeTranslate(node.name) : (node.translated_name ?? node.name)
	);

	async function loadAssets() {
		if (isLoading) return;
		isLoading = true;
		try {
			const res = await fetch(`/assets?asset_class=${node.id}&limit=${PAGE_SIZE}&offset=${loaded}`);
			if (res.ok) {
				const data = await res.json();
				assets = [...assets, ...(data.results ?? [])];
				loaded = assets.length;
				total = data.count ?? loaded;
			}
		} catch (e) {
			console.error('AssetClassNode: failed to fetch assets', e);
		} finally {
			isLoading = false;
		}
	}

	function toggle() {
		isExpanded = !isExpanded;
		if (isExpanded && node.direct_count > 0 && assets.length === 0) loadAssets();
	}
</script>

<li class="list-none m-0 p-0">
	<div class="flex items-center gap-1" style="padding-left: {Math.min(depth, 8) * 16}px">
		<button
			type="button"
			onclick={toggle}
			class="flex items-center gap-2 flex-1 min-w-0 px-2 py-1.5 rounded text-left text-sm hover:bg-surface-100-900 transition-colors"
			aria-expanded={isExpanded}
		>
			<i
				class="fa-solid fa-chevron-right text-[9px] text-surface-500 transition-transform duration-150 {isExpanded
					? 'rotate-90'
					: ''} {hasChildren || node.direct_count > 0 ? '' : 'invisible'}"
			></i>
			<i
				class="fa-solid fa-sitemap text-xs {node.is_visible
					? 'text-surface-500'
					: 'text-surface-400'}"
			></i>
			<span class="truncate {node.is_visible ? '' : 'italic text-surface-500'}">{label}</span>
			{#if node.total_count > 0}
				<span class="badge preset-tonal-primary text-xs shrink-0">{node.total_count}</span>
			{/if}
			{#if node.direct_count > 0 && node.direct_count !== node.total_count}
				<span class="text-[10px] text-surface-500 shrink-0">({node.direct_count})</span>
			{/if}
		</button>
	</div>

	{#if isExpanded}
		{#if node.direct_count > 0}
			<ul class="list-none m-0 p-0" style="padding-left: {Math.min(depth, 8) * 16 + 30}px">
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

		{#if hasChildren}
			<ul class="list-none m-0 p-0">
				{#each visibleChildren as child (child.id)}
					<AssetClassNode node={child} {hideEmpty} depth={depth + 1} />
				{/each}
			</ul>
		{/if}
	{/if}
</li>
