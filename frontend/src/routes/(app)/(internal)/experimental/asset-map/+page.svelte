<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount, untrack } from 'svelte';
	import AssetMap from './AssetMap.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let query = $state('');
	let results = $state<any[]>([]);
	let timer: ReturnType<typeof setTimeout> | undefined;

	const focusNode = $derived(data.graph?.nodes.find((n: any) => n.id === data.graph?.focus));

	function navigate(changes: Record<string, string | null>) {
		const url = new URL(page.url);
		for (const [key, value] of Object.entries(changes)) {
			if (value) url.searchParams.set(key, value);
			else url.searchParams.delete(key);
		}
		url.searchParams.delete('expand');
		url.searchParams.delete('reveal');
		goto(url, { invalidateAll: true, noScroll: true });
	}

	type Crumb = { id: string; name: string };
	const TRAIL_KEY = 'assetMap:trail';
	let trail = $state<Crumb[]>([]);

	function setTrail(next: Crumb[]) {
		trail = next;
		try {
			sessionStorage.setItem(TRAIL_KEY, JSON.stringify(next));
		} catch {
			// ignore storage errors
		}
	}

	function trimAt(focus: string) {
		const index = trail.findIndex((c) => c.id === focus);
		if (index >= 0) setTrail(trail.slice(0, index));
	}

	onMount(() => {
		try {
			const saved = JSON.parse(sessionStorage.getItem(TRAIL_KEY) ?? '[]');
			if (Array.isArray(saved)) trail = saved;
		} catch {
			trail = [];
		}
		trimAt(data.focus);
	});

	let lastFocus = data.focus;
	$effect(() => {
		const focus = data.focus;
		untrack(() => {
			if (focus === lastFocus) return;
			lastFocus = focus;
			trimAt(focus);
		});
	});

	function refocus(id: string) {
		query = '';
		results = [];
		if (focusNode && !focusNode.hidden && focusNode.id !== id) {
			const current = { id: focusNode.id, name: focusNode.name ?? '' };
			setTrail([...trail.filter((c) => c.id !== current.id && c.id !== id), current].slice(-8));
		}
		navigate({ focus: id });
	}

	function grow(param: 'expand' | 'reveal', id: string) {
		const url = new URL(page.url);
		if (!url.searchParams.getAll(param).includes(id)) url.searchParams.append(param, id);
		goto(url, { invalidateAll: true, noScroll: true, keepFocus: true });
	}

	function onSearch() {
		clearTimeout(timer);
		const q = query.trim();
		if (q.length < 2) {
			results = [];
			return;
		}
		timer = setTimeout(async () => {
			const res = await fetch(`/assets?search=${encodeURIComponent(q)}&limit=15`).catch(() => null);
			const body = res?.ok ? await res.json() : { results: [] };
			if (query.trim() === q) results = body.results ?? [];
		}, 250);
	}
</script>

<div class="flex flex-col h-[calc(100vh-9rem)]">
	<div class="flex flex-wrap items-center gap-3 mb-3 bg-surface-50-950 shadow-sm rounded-base p-3">
		<h4 class="font-bold text-surface-800-200">
			<i class="fa-solid fa-sitemap mr-2"></i>Asset dependency map
		</h4>
		<span
			class="text-xs text-surface-500 px-2 py-0.5 rounded bg-surface-100-900 border border-surface-200-800"
		>
			experimental
		</span>
		{#if focusNode}
			<nav class="flex items-center gap-1.5 text-sm min-w-0" aria-label="Focus trail">
				<span class="text-surface-600-400">Focus:</span>
				{#each trail as crumb (crumb.id)}
					<button
						type="button"
						class="text-surface-600-400 hover:text-primary-500 hover:underline truncate max-w-[10rem] cursor-pointer"
						title={crumb.name}
						onclick={() => refocus(crumb.id)}
					>
						{crumb.name}
					</button>
					<i class="fa-solid fa-chevron-right text-[9px] text-surface-400"></i>
				{/each}
				<span class="font-semibold text-surface-800-200 truncate max-w-xs">{focusNode.name}</span>
			</nav>
		{/if}
		<div class="flex-1"></div>
		<div class="relative">
			<input
				type="search"
				placeholder="Focus on an asset…"
				bind:value={query}
				oninput={onSearch}
				class="w-64 rounded-lg border-surface-300-700 bg-surface-100-900 text-surface-700-300 sm:text-sm"
			/>
			{#if results.length}
				<ul
					class="absolute right-0 z-20 mt-1 w-80 max-h-72 overflow-y-auto bg-surface-50-950 border border-surface-300-700 rounded-base shadow-lg p-1"
				>
					{#each results as result (result.id)}
						<li>
							<button
								type="button"
								class="w-full text-left px-2 py-1.5 rounded hover:bg-surface-200-800 cursor-pointer"
								onclick={() => refocus(result.id)}
							>
								<div class="text-sm font-semibold text-surface-800-200 truncate">
									{result.name}
								</div>
								<div class="text-[11px] text-surface-500 truncate">
									<i class="fa-solid fa-sitemap text-[9px] mr-1"></i>{result.folder?.str}
								</div>
							</button>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
		<div class="flex rounded-lg border border-surface-300-700 overflow-hidden text-sm">
			<button
				type="button"
				class="px-3 py-1.5 {data.mode === 'chain'
					? 'preset-filled-primary-500'
					: 'bg-surface-100-900 text-surface-700-300'}"
				title="Everything this asset depends on, and everything depending on it"
				onclick={() => navigate({ mode: 'chain' })}
			>
				Dependency chain
			</button>
			<button
				type="button"
				class="px-3 py-1.5 {data.mode === 'connected'
					? 'preset-filled-primary-500'
					: 'bg-surface-100-900 text-surface-700-300'}"
				title="Every asset reachable through links, in any direction"
				onclick={() => navigate({ mode: 'connected' })}
			>
				Everything connected
			</button>
		</div>
		<label class="text-sm text-surface-700-300 flex items-center gap-2">
			Reach
			<select
				value={data.maxHops}
				onchange={(e) => navigate({ max_hops: e.currentTarget.value || null })}
				class="rounded-lg border-surface-300-700 bg-surface-100-900 text-surface-700-300 sm:text-sm"
			>
				<option value="">All links</option>
				<option value="1">1 link</option>
				<option value="2">2 links</option>
				<option value="3">3 links</option>
			</select>
		</label>
	</div>

	<div class="flex-1 min-h-0">
		{#if data.graph}
			{#key `${data.focus}|${data.mode}|${data.maxHops}`}
				<AssetMap
					graph={data.graph}
					assetModel={data.assetModel}
					onRefocus={refocus}
					onExpand={(id) => grow('expand', id)}
					onReveal={(id) => grow('reveal', id)}
				/>
			{/key}
		{:else}
			<div
				class="h-full flex items-center justify-center bg-surface-50-950 rounded-base border border-dashed border-surface-300-700 text-surface-500"
			>
				<div class="text-center">
					<i class="fa-solid fa-sitemap text-4xl mb-3 text-surface-300"></i>
					<p class="text-sm">
						{#if data.graphError === 'notFound'}
							This asset does not exist or you cannot view it.
						{:else if data.graphError}
							The dependency map could not be loaded.
						{:else}
							Search for an asset above to map everything it depends on, across domains.
						{/if}
					</p>
				</div>
			</div>
		{/if}
	</div>
</div>
