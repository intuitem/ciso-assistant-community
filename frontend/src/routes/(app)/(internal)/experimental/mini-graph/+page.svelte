<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import GraphPanel from './GraphPanel.svelte';
	import { NODE_BY_ID, TYPE_META, neighborsOf } from './universe';
	import type { LiveNode } from './accretion';

	$pageTitle = 'Mini graph explorer';

	const STARTERS = [
		{ id: 'ac-fde', label: 'Applied control' },
		{ id: 'rs-theft', label: 'Risk scenario' },
		{ id: 'as-laptops', label: 'Asset' },
		{ id: 'au-iso', label: 'Audit' }
	];

	let rootId = $state('ac-fde');
	let panelOpen = $state(false);
	let toast = $state('');

	const root = $derived(NODE_BY_ID.get(rootId)!);
	const meta = $derived(TYPE_META[root.type]);
	const directCount = $derived(new Set(neighborsOf(rootId).map((n) => n.id)).size);

	function openObject(node: LiveNode) {
		// Fixture ids have no page. Wired up, this is an Anchor to /{urlModel}/{uuid}.
		toast = `Would navigate to the ${TYPE_META[node.type].label.toLowerCase()} "${node.name}"`;
		setTimeout(() => (toast = ''), 2500);
	}
</script>

<div class="flex flex-col gap-4">
	<div class="card bg-surface-50-950 shadow-sm p-3 flex flex-wrap items-center gap-3">
		<h4 class="font-bold text-surface-800-200">
			<i class="fa-solid fa-circle-nodes mr-2"></i>Mini graph explorer
		</h4>
		<span
			class="text-xs text-surface-500 px-2 py-0.5 rounded bg-surface-100-900 border border-surface-200-800"
			>mock data</span
		>
		<span class="text-xs text-surface-500">Pretend you are on the detail page of:</span>
		{#each STARTERS as s}
			<button
				class="btn btn-sm {rootId === s.id ? 'preset-filled-primary-500' : 'preset-tonal'}"
				onclick={() => (rootId = s.id)}>{s.label}</button
			>
		{/each}
	</div>

	<!-- Stand-in for DetailView: only the action bar and the field list matter here. -->
	<div class="card bg-surface-50-950 shadow-lg p-4">
		<div class="flex items-start gap-3 mb-4">
			<i class="fa-solid {meta.icon} mt-1 text-lg" style="color:{meta.color}"></i>
			<div class="flex-1 min-w-0">
				<div class="text-xs text-surface-500">{meta.label}</div>
				<h3 class="font-semibold text-lg">{root.name}</h3>
			</div>
			<div class="flex items-center gap-2">
				<button class="btn preset-tonal" onclick={() => (panelOpen = true)}>
					<i class="fa-solid fa-circle-nodes mr-2"></i>Relations
					<span class="ml-2 text-xs opacity-70 tabular-nums">{directCount}</span>
				</button>
				<button class="btn preset-filled-primary-500" disabled>
					<i class="fa-solid fa-pen-to-square mr-2"></i>Edit
				</button>
			</div>
		</div>

		<dl class="divide-y divide-surface-100-900 text-sm border-t border-surface-100-900">
			{#each Object.entries(root.meta ?? {}) as [k, v]}
				<div class="grid grid-cols-4 gap-2 py-2">
					<dt class="font-medium text-surface-700-300 capitalize">{k}</dt>
					<dd class="col-span-3 text-surface-600-400">{v}</dd>
				</div>
			{/each}
			<div class="grid grid-cols-4 gap-2 py-2 opacity-40">
				<dt class="font-medium">…</dt>
				<dd class="col-span-3">the rest of the real detail view, then its tabs</dd>
			</div>
		</dl>
	</div>
</div>

<GraphPanel
	open={panelOpen}
	{rootId}
	onClose={() => (panelOpen = false)}
	onOpenObject={openObject}
/>

{#if toast}
	<div
		class="fixed bottom-4 left-4 z-50 card bg-surface-950-50 text-surface-50-950 px-4 py-2 text-sm shadow-xl"
	>
		{toast}
	</div>
{/if}
