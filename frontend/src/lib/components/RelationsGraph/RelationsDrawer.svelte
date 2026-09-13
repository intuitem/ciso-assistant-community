<script lang="ts">
	import { fly } from 'svelte/transition';
	import { page } from '$app/state';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import RelationsGraph from './RelationsGraph.svelte';
	import { metaFor } from './meta';
	import { RELATION_MAP } from './relations';
	import type { Neighborhood } from './types';
	import type { PlacedNode } from './layout';

	interface Props {
		open: boolean;
		urlModel: string;
		id: string;
		onClose: () => void;
	}

	let { open, urlModel, id, onClose }: Props = $props();

	interface Focus {
		urlModel: string;
		id: string;
	}

	// The drawer owns what it is looking at, so re-centring explores without
	// navigating the page underneath. null = still on the record the page is on.
	let explored: Focus | null = $state(null);
	let trail: Focus[] = $state([]);
	const focus = $derived<Focus>(explored ?? { urlModel, id });

	let data: Neighborhood | null = $state(null);
	let loading = $state(false);
	let loadError = $state('');
	let selected: PlacedNode | null = $state(null);
	let fanCap = $state(5);
	let showLabels = $state(true);
	let wide = $state(false);
	let filterOpen = $state(false);
	let hidden = $state(new Set<string>(['folders']));
	let stats = $state({ nodes: 0, collapsed: 0 });

	// The chat launcher is fixed at bottom-right above everything (z-950), so the
	// footer keeps its corner clear rather than hiding controls underneath it.
	const chatBubble = $derived(Boolean(page.data?.featureflags?.chat_mode));

	$effect(() => {
		urlModel;
		id;
		explored = null;
		trail = [];
	});

	$effect(() => {
		if (!open) return;
		const { urlModel: m, id: objectId } = focus;
		let stale = false;
		loading = true;
		loadError = '';
		selected = null;
		fetch(`/${m}/${objectId}/neighborhood`)
			.then(async (res) => {
				if (!res.ok) throw new Error(String(res.status));
				const body = await res.json();
				if (!stale) data = body;
			})
			.catch(() => {
				if (!stale) {
					data = null;
					loadError = 'Could not load the relations of this object.';
				}
			})
			.finally(() => {
				if (!stale) loading = false;
			});
		return () => {
			stale = true;
		};
	});

	const rootMeta = $derived(metaFor(focus.urlModel));
	const canExplore = (node: PlacedNode) => node.urlModel in RELATION_MAP;

	function reroot(node: PlacedNode) {
		trail = [...trail, focus];
		explored = { urlModel: node.urlModel, id: node.id };
	}
	function back() {
		if (!trail.length) return;
		const previous = trail[trail.length - 1];
		trail = trail.slice(0, -1);
		explored = trail.length || previous.id !== id ? previous : null;
	}
	function toggleType(model: string) {
		const next = new Set(hidden);
		next.has(model) ? next.delete(model) : next.add(model);
		hidden = next;
	}

	const presentTypes = $derived(
		[...new Set((data?.nodes ?? []).map((n) => n.urlModel))].sort((a, b) =>
			metaFor(a).label.localeCompare(metaFor(b).label)
		)
	);
</script>

<svelte:window
	onkeydown={(e) => {
		if (e.key === 'Escape' && open) onClose();
	}}
/>

{#if open}
	<!-- No backdrop on purpose: the graph is read against the record it belongs to,
	     so the detail view stays visible and usable behind it. -->
	<aside
		class="fixed top-0 right-0 bottom-0 z-50 flex flex-col bg-surface-50-950 border-l-2 border-surface-300-700
			shadow-[-16px_0_48px_-12px_rgba(2,6,23,0.38)] dark:shadow-[-16px_0_48px_-12px_rgba(0,0,0,0.75)]"
		style="width: min({wide ? '1100px' : '580px'}, 96vw)"
		transition:fly={{ x: 420, duration: 220 }}
		aria-label="Relations"
	>
		<header class="flex items-start gap-2 p-3 border-b border-surface-200-800">
			{#if trail.length}
				<button class="btn btn-sm preset-tonal" onclick={back} title="Back" aria-label="Back">
					<i class="fa-solid fa-arrow-left"></i>
				</button>
			{/if}
			<i class="fa-solid {rootMeta.icon} mt-1.5" style="color:{rootMeta.color}"></i>
			<div class="flex-1 min-w-0">
				<div class="text-xs text-surface-500">{rootMeta.label}</div>
				<div class="font-semibold truncate" title={data?.root.name}>
					{data?.root.name ?? '…'}
				</div>
			</div>
			<button
				class="btn btn-sm preset-tonal"
				onclick={() => (wide = !wide)}
				title={wide ? 'Narrow' : 'Widen'}
				aria-label="Toggle width"
			>
				<i class="fa-solid {wide ? 'fa-right-to-bracket' : 'fa-left-right'}"></i>
			</button>
			<button class="btn btn-sm preset-tonal" onclick={onClose} title="Close" aria-label="Close">
				<i class="fa-solid fa-xmark"></i>
			</button>
		</header>

		<div class="relative flex-1 min-h-0 bg-surface-100-900">
			{#if loading}
				<div class="absolute inset-0 grid place-items-center text-surface-500 text-sm z-10">
					<i class="fa-solid fa-circle-notch fa-spin text-2xl"></i>
				</div>
			{:else if loadError}
				<div class="absolute inset-0 grid place-items-center text-surface-500 text-sm p-6 text-center">
					{loadError}
				</div>
			{:else if data && data.nodes.length === 0}
				<div class="absolute inset-0 grid place-items-center text-surface-500 text-sm p-6 text-center">
					<div>
						<i class="fa-solid fa-circle-nodes text-3xl mb-3 opacity-40"></i>
						<p>Nothing is linked to this object yet.</p>
					</div>
				</div>
			{/if}
			{#if data && !loading && data.nodes.length > 0}
				<RelationsGraph
					{data}
					{fanCap}
					{hidden}
					{showLabels}
					onSelect={(n) => (selected = n)}
					onStats={(s) => (stats = s)}
				/>
			{/if}

			{#if selected}
				{@const meta = metaFor(selected.urlModel)}
				<div
					class="absolute bottom-2 left-2 card bg-surface-50-950 border border-surface-200-800 shadow-lg p-3 text-sm {chatBubble
						? 'right-20'
						: 'right-2'}"
				>
					<div class="flex items-start gap-2">
						<i class="fa-solid {meta.icon} mt-1" style="color:{meta.color}"></i>
						<div class="flex-1 min-w-0">
							<div class="text-xs text-surface-500">{meta.label}</div>
							<div class="font-semibold truncate" title={selected.name}>{selected.name}</div>
							{#if selected.meta}
								<div class="flex flex-wrap gap-x-3 gap-y-0.5 mt-1 text-xs text-surface-600-400">
									{#each Object.entries(selected.meta) as [k, v]}
										<span><span class="opacity-60">{k}:</span> {v}</span>
									{/each}
								</div>
							{/if}
						</div>
						<div class="flex items-center gap-1">
							{#if canExplore(selected)}
								<button
									class="btn btn-sm preset-tonal"
									title="Explore this object's relations"
									aria-label="Re-centre"
									onclick={() => reroot(selected!)}><i class="fa-solid fa-crosshairs"></i></button
								>
							{/if}
							<Anchor
								breadcrumbAction="push"
								href={`/${selected.urlModel}/${selected.id}`}
								label="Open"
								class="btn btn-sm preset-tonal"
								title="Open the object page"
								><i class="fa-solid fa-arrow-up-right-from-square"></i></Anchor
							>
							<button
								class="btn btn-sm preset-tonal"
								title="Close"
								aria-label="Close"
								onclick={() => (selected = null)}><i class="fa-solid fa-xmark"></i></button
							>
						</div>
					</div>
				</div>
			{/if}
		</div>

		<footer class="border-t border-surface-200-800 px-3 py-2 {chatBubble ? 'pr-20' : ''}">
			<div class="flex items-center gap-2 text-xs text-surface-500">
				<span class="tabular-nums">
					{stats.nodes} related{stats.collapsed ? ` · ${stats.collapsed} collapsed` : ''}
				</span>
				<div class="flex-1"></div>
				<span class="uppercase tracking-wide">Fan-out</span>
				<input type="range" min="2" max="15" bind:value={fanCap} class="w-16 accent-primary-500" />
				<span class="w-4 text-center tabular-nums">{fanCap}</span>
				<button
					class="btn btn-sm preset-tonal"
					onclick={() => (showLabels = !showLabels)}
					title="Labels"
					aria-label="Toggle labels"
				>
					<i class="fa-solid fa-tag {showLabels ? '' : 'opacity-40'}"></i>
				</button>
				<button class="btn btn-sm preset-tonal" onclick={() => (filterOpen = !filterOpen)}>
					<i class="fa-solid fa-filter"></i>
					{#if hidden.size}<span class="ml-1">{hidden.size}</span>{/if}
				</button>
			</div>
			{#if filterOpen}
				<div class="flex flex-wrap gap-1 mt-2">
					{#each presentTypes as model}
						{@const tm = metaFor(model)}
						{@const off = hidden.has(model)}
						<button
							class="text-[10px] px-1.5 py-0.5 rounded-full border transition {off
								? 'opacity-35 border-surface-300-700'
								: 'border-transparent'}"
							style={off ? '' : `background:${tm.color}22;color:${tm.color}`}
							onclick={() => toggleType(model)}
							title={off ? 'Show' : 'Hide'}
						>
							{tm.label}
						</button>
					{/each}
				</div>
			{/if}
		</footer>
	</aside>
{/if}
