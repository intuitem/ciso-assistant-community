<script lang="ts">
	import { fly } from 'svelte/transition';
	import { m } from '$paraglide/messages';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import RelationsGraph from './RelationsGraph.svelte';
	import { metaFor } from './meta';
	import { urlModelForDjangoName } from '$lib/utils/crud';
	import {
		createGraph,
		merge,
		collapse,
		setLoading,
		canExpand,
		NODE_BUDGET,
		MAX_HOP,
		type LiveGraph,
		type LiveNode
	} from './accretion';
	import type { Neighborhood } from './types';

	interface Props {
		open: boolean;
		urlModel: string;
		id: string;
		name?: string;
		onClose: () => void;
	}

	let { open, urlModel, id, name = '', onClose }: Props = $props();

	let graph: LiveGraph = $state(createGraph({ id, urlModel, name }));
	let selected: LiveNode | null = $state(null);
	const DEFAULT_HIDDEN = ['perimeters'];
	const DEFAULT_FAN_CAP = 5;

	let fanCap = $state(DEFAULT_FAN_CAP);
	let showLabels = $state(true);
	let wide = $state(false);
	let filterOpen = $state(false);
	let hidden = $state(new Set<string>(DEFAULT_HIDDEN));
	let opened = $state(new Set<string>());
	let booting = $state(false);
	let bootError = $state('');

	// The chat launcher sits bottom-right at z-950; keep that corner clear.
	const chatBubble = $derived(Boolean(page.data?.featureflags?.chat_mode));

	const cache = new Map<string, Neighborhood>();
	const inflight = new Map<string, Promise<Neighborhood>>();

	async function neighborhood(model: string, objectId: string): Promise<Neighborhood> {
		const key = `${model}/${objectId}`;
		const hit = cache.get(key);
		if (hit) return hit;
		const pending = inflight.get(key);
		if (pending) return pending;
		const request = fetch(`/${model}/${objectId}/neighborhood`)
			.then(async (res) => {
				if (!res.ok) throw new Error(String(res.status));
				const body: Neighborhood = await res.json();
				// Route segments are the frontend's to know.
				for (const n of [body.root, ...body.nodes]) {
					const resolved = n.model ? urlModelForDjangoName(n.model) : null;
					n.navigable = Boolean(resolved);
					if (resolved) n.urlModel = resolved;
				}
				cache.set(key, body);
				return body;
			})
			.finally(() => inflight.delete(key));
		inflight.set(key, request);
		return request;
	}

	$effect(() => {
		if (!open) return;
		urlModel;
		id;
		reset();
	});

	function reload() {
		cache.clear();
		hidden = new Set(DEFAULT_HIDDEN);
		fanCap = DEFAULT_FAN_CAP;
		return reset();
	}

	async function reset() {
		graph = createGraph({ id, urlModel, name });
		selected = null;
		opened = new Set();
		bootError = '';
		booting = true;
		try {
			const payload = await neighborhood(urlModel, id);
			graph = merge(createGraph(payload.root), id, payload, { fanCap, hidden, opened });
		} catch {
			bootError = m.relationsLoadFailed();
		} finally {
			booting = false;
		}
	}

	async function expandNode(node: LiveNode) {
		if (node.hop >= MAX_HOP) {
			graph = {
				...graph,
				notice: m.relationsMaxHop({ hops: MAX_HOP })
			};
			return;
		}
		if (!canExpand(node) || node.loading) return;
		graph = setLoading(graph, node.id, true);
		try {
			const payload = await neighborhood(node.urlModel, node.id);
			graph = merge(graph, node.id, payload, { fanCap, hidden, opened });
		} catch {
			graph = { ...setLoading(graph, node.id, false), notice: m.relationsLoadNodeFailed() };
		}
	}

	function openAggregate(node: LiveNode) {
		if (!node.aggregate) return;
		const { parentId, group } = node.aggregate;
		const parent = graph.nodes.get(parentId);
		if (!parent) return;
		const payload = cache.get(`${parent.urlModel}/${parentId}`);
		if (!payload) return;
		const next = new Set(opened);
		next.add(`${parentId}|${group}`);
		opened = next;
		// Collapse first so the parent's fan is laid out once, newcomers included.
		graph = merge(collapse(graph, parentId), parentId, payload, { fanCap, hidden, opened: next });
	}

	function onNode(node: LiveNode) {
		if (node.aggregate) {
			selected = null;
			openAggregate(node);
			return;
		}
		selected = node;
		if (node.expanded) graph = collapse(graph, node.id);
		else expandNode(node);
	}

	function goToNode(node: LiveNode) {
		onClose();
		goto(`/${node.urlModel}/${node.id}`);
	}

	function toggleType(model: string) {
		const next = new Set(hidden);
		next.has(model) ? next.delete(model) : next.add(model);
		hidden = next;
		reset();
	}

	const rootNode = $derived(graph.nodes.get(id));
	const rootMeta = $derived(metaFor(urlModel));
	const expandable = $derived([...graph.nodes.values()].filter(canExpand));
	// Hidden types stay listed, or their own chips vanish with them.
	const filterTypes = $derived(
		[...new Set([...[...graph.nodes.values()].map((n) => n.urlModel), ...hidden])].sort((a, b) =>
			metaFor(a).label.localeCompare(metaFor(b).label)
		)
	);

	async function expandAll() {
		for (const node of expandable.slice(0, 10)) {
			await expandNode(node);
			if (graph.notice) break;
		}
	}
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
		aria-label={m.relationsGraph()}
	>
		<header class="flex items-start gap-2 p-3 border-b border-surface-200-800">
			<i class="fa-solid {rootMeta.icon} mt-1.5" style="color:{rootMeta.color}"></i>
			<div class="flex-1 min-w-0">
				<div class="text-xs text-surface-500">{rootMeta.label}</div>
				<div class="font-semibold truncate" title={rootNode?.name}>{rootNode?.name ?? name}</div>
			</div>
			<button
				class="btn btn-sm preset-tonal"
				onclick={reload}
				title={m.relationsStartOver()}
				aria-label={m.relationsStartOver()}
			>
				<i class="fa-solid fa-rotate-left"></i>
			</button>
			<button
				class="btn btn-sm preset-tonal"
				onclick={() => (wide = !wide)}
				title={wide ? m.narrow() : m.widen()}
				aria-label={m.relationsToggleWidth()}
			>
				<i class="fa-solid {wide ? 'fa-right-to-bracket' : 'fa-left-right'}"></i>
			</button>
			<button
				class="btn btn-sm preset-tonal"
				onclick={onClose}
				title={m.close()}
				aria-label={m.close()}
			>
				<i class="fa-solid fa-xmark"></i>
			</button>
		</header>

		<div class="relative flex-1 min-h-0 bg-surface-100-900">
			{#if booting}
				<div class="absolute inset-0 grid place-items-center text-surface-500 z-10">
					<i class="fa-solid fa-circle-notch fa-spin text-2xl"></i>
				</div>
			{:else if bootError}
				<div
					class="absolute inset-0 grid place-items-center text-surface-500 text-sm p-6 text-center"
				>
					{bootError}
				</div>
			{:else if graph.nodes.size <= 1}
				<div
					class="absolute inset-0 grid place-items-center text-surface-500 text-sm p-6 text-center"
				>
					<div>
						<i class="fa-solid fa-circle-nodes text-3xl mb-3 opacity-40"></i>
						<p>{m.relationsNoLinks()}</p>
					</div>
				</div>
			{:else}
				<RelationsGraph
					{graph}
					{showLabels}
					onNodeClick={onNode}
					onNodeDoubleClick={(n) =>
						!n.aggregate && n.hop > 0 && n.navigable !== false && goToNode(n)}
				/>
			{/if}

			{#if graph.notice}
				<div
					class="absolute top-2 left-2 right-2 card preset-tonal-warning px-3 py-2 text-xs shadow-lg"
				>
					{graph.notice}
				</div>
			{/if}

			{#if selected && selected.hop > 0}
				{@const meta = metaFor(selected.urlModel)}
				<div
					class="absolute bottom-2 left-2 card bg-surface-50-950 border border-surface-200-800 shadow-lg p-3 text-sm {chatBubble
						? 'right-20'
						: 'right-2'}"
				>
					<div class="flex items-start gap-2">
						<i class="fa-solid {meta.icon} mt-1" style="color:{meta.color}"></i>
						<div class="flex-1 min-w-0">
							<div class="text-xs text-surface-500">
								{meta.label}
								{#if selected.frontier}· <span class="opacity-70">{m.relationsEdgeOfView()}</span
									>{/if}
							</div>
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
							{#if selected.navigable !== false}
								<Anchor
									breadcrumbAction="push"
									href={`/${selected.urlModel}/${selected.id}`}
									label={m.open()}
									class="btn btn-sm preset-tonal"
									title={m.relationsOpenObjectPage()}
									><i class="fa-solid fa-arrow-up-right-from-square"></i></Anchor
								>
							{/if}
							<button
								class="btn btn-sm preset-tonal"
								title={m.close()}
								aria-label={m.close()}
								onclick={() => (selected = null)}><i class="fa-solid fa-xmark"></i></button
							>
						</div>
					</div>
				</div>
			{/if}
		</div>

		<footer class="border-t border-surface-200-800 px-3 py-2 {chatBubble ? 'pr-20' : ''}">
			<div class="flex flex-wrap items-center gap-2 text-xs text-surface-500">
				<span class="tabular-nums"
					>{m.relationsRelatedCount({ shown: graph.nodes.size - 1, budget: NODE_BUDGET })}</span
				>
				{#if expandable.length}
					<span class="opacity-70"
						>· {m.relationsExpandableCount({ count: expandable.length })}</span
					>
				{/if}
				<div class="flex-1"></div>
				{#if expandable.length && expandable.length <= 10}
					<button class="btn btn-sm preset-tonal" onclick={expandAll}>
						<i class="fa-solid fa-arrows-left-right-to-line mr-1"></i>{m.expandAll()}
					</button>
				{/if}
				<span class="uppercase tracking-wide" title={m.relationsPerRelationHint()}
					>{m.relationsPerRelation()}</span
				>
				<input
					type="range"
					min="2"
					max="12"
					bind:value={fanCap}
					onchange={reset}
					title={m.relationsPerRelationHint()}
					class="w-16 accent-primary-500"
					aria-label={m.relationsObjectsPerRelation()}
				/>
				<span class="w-4 text-center tabular-nums">{fanCap}</span>
				<button
					class="btn btn-sm preset-tonal"
					onclick={() => (showLabels = !showLabels)}
					title={m.labels()}
					aria-label={m.relationsToggleLabels()}
				>
					<i class="fa-solid fa-tag {showLabels ? '' : 'opacity-40'}"></i>
				</button>
				<button
					class="btn btn-sm {hidden.size ? 'preset-filled-primary-500' : 'preset-tonal'}"
					onclick={() => (filterOpen = !filterOpen)}
					title={m.relationsFilterByType()}
				>
					<i class="fa-solid fa-filter"></i>
					{#if hidden.size}<span class="ml-1">{hidden.size}</span>{/if}
				</button>
			</div>
			{#if filterOpen}
				<div class="flex items-center gap-2 mt-2">
					<span class="text-[10px] uppercase tracking-wide text-surface-500"
						>{m.relationsShownTypes()}</span
					>
					<div class="flex-1"></div>
					{#if hidden.size}
						<button
							class="text-[10px] underline text-surface-600-400"
							onclick={() => {
								hidden = new Set();
								reset();
							}}>{m.relationsShowAllHidden({ count: hidden.size })}</button
						>
					{/if}
				</div>
				<div class="flex flex-wrap gap-1 mt-1">
					{#each filterTypes as model}
						{@const tm = metaFor(model)}
						{@const off = hidden.has(model)}
						<button
							class="text-[10px] px-1.5 py-0.5 rounded-full border transition {off
								? 'opacity-35 border-surface-300-700'
								: 'border-transparent'}"
							style={off ? '' : `background:${tm.color}22;color:${tm.color}`}
							onclick={() => toggleType(model)}
							title={off ? m.show() : m.hide()}
						>
							{tm.label}
						</button>
					{/each}
				</div>
			{/if}
		</footer>
	</aside>
{/if}
