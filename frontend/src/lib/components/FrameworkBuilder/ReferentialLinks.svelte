<script lang="ts">
	import { getBuilderContext, type BuilderNode } from './builder-state';
	import {
		apiBrowseReferenceLibrary,
		apiCreateReferential,
		type ReferentialCatalogItem,
		type ReferentialCatalogSource
	} from './builder-api';
	import { getReferentialCatalog } from './referential-catalog';
	import { m } from '$paraglide/messages';
	import { safeTranslate } from '$lib/utils/i18n';

	interface Props {
		node: BuilderNode;
		kind: 'threats' | 'reference_controls';
	}

	let { node, kind }: Props = $props();

	const builder = getBuilderContext();
	const catalogStore = getReferentialCatalog();
	const isControl = kind === 'reference_controls';

	// Mirrors the backend enums (core.models ReferenceControl).
	const CATEGORIES = ['policy', 'process', 'technical', 'physical', 'procedure'];
	const CSF_FUNCTIONS = ['govern', 'identify', 'protect', 'detect', 'respond', 'recover'];

	let open = $state(false);
	let tab: 'existing' | 'create' = $state('existing');
	let search = $state('');
	let browseError = $state(false);
	let createRefId = $state('');
	let createName = $state('');
	let createDescription = $state('');
	let createCategory = $state('');
	let createCsfFunction = $state('');
	let createError = $state('');
	let busy = $state(false);

	// Deduplicated defensively: the pill list keys on the URN, and raw draft
	// content may carry repeats the bridge has not normalized yet.
	const current = $derived([...new Set(node.node[kind] ?? [])]);
	const catalogReady = $derived($catalogStore?.status === 'ready');

	const sources = $derived($catalogStore?.catalog?.sources ?? []);

	const labelByUrn = $derived.by(() => {
		const map = new Map<string, string>();
		for (const source of sources) {
			for (const item of source[kind] ?? []) {
				map.set(item.urn, item.ref_id || item.name || item.urn);
			}
		}
		return map;
	});

	function labelFor(urn: string): string {
		return labelByUrn.get(urn) ?? urn.split(':').slice(-1)[0];
	}

	const pickable = $derived.by(() => {
		const linked = new Set(current);
		const term = search.trim().toLowerCase();
		const entries: { item: ReferentialCatalogItem; source: ReferentialCatalogSource }[] = [];
		for (const source of sources) {
			for (const item of source[kind] ?? []) {
				if (linked.has(item.urn)) continue;
				linked.add(item.urn); // same URN from two sources → list it once
				if (
					term &&
					!`${item.ref_id ?? ''} ${item.name ?? ''} ${item.urn}`.toLowerCase().includes(term)
				) {
					continue;
				}
				entries.push({ item, source });
			}
		}
		return entries.slice(0, 50);
	});

	const browsableLibraries = $derived.by(() => {
		const shown = new Set(sources.map((s) => s.library_urn));
		return ($catalogStore?.catalog?.libraries ?? []).filter((l) => !shown.has(l.library_urn));
	});

	function attach(urn: string) {
		builder.updateNode(node.node.id, { [kind]: [...current, urn] });
	}

	function detach(urn: string) {
		builder.updateNode(node.node.id, {
			[kind]: current.filter((linked) => linked !== urn)
		});
	}

	async function browseLibrary(event: Event) {
		const select = event.currentTarget as HTMLSelectElement;
		const libraryUrn = select.value;
		select.value = '';
		if (!libraryUrn) return;
		busy = true;
		browseError = false;
		try {
			const source = await apiBrowseReferenceLibrary(builder.apiTarget, libraryUrn);
			// Broadcast to the shared catalog so a library browsed in one picker
			// is visible to every instance without re-fetching (mirrors
			// createNew()). The guard avoids a duplicate source if two pickers
			// browse the same library concurrently.
			catalogStore?.update((state) => {
				const catalogSources = state.catalog?.sources;
				if (catalogSources && !catalogSources.some((s) => s.library_urn === source.library_urn)) {
					catalogSources.push(source);
				}
				return { ...state };
			});
		} catch {
			browseError = true;
		} finally {
			busy = false;
		}
	}

	async function createNew() {
		const object: Record<string, unknown> = {
			ref_id: createRefId.trim(),
			name: createName.trim()
		};
		if (createDescription.trim()) object.description = createDescription.trim();
		if (isControl && createCategory) object.category = createCategory;
		if (isControl && createCsfFunction) object.csf_function = createCsfFunction;
		busy = true;
		createError = '';
		try {
			const created = await apiCreateReferential(builder.apiTarget, kind, object);
			// Surface the new draft-owned object to every picker instance.
			catalogStore?.update((state) => {
				state.catalog?.sources
					.find((source) => source.kind === 'draft')
					?.[kind].push({
						urn: created.urn,
						ref_id: (created.ref_id as string) ?? null,
						name: (created.name as string) ?? null
					});
				return { ...state };
			});
			attach(created.urn);
			createRefId = '';
			createName = '';
			createDescription = '';
			createCategory = '';
			createCsfFunction = '';
			open = false;
			tab = 'existing';
		} catch (error) {
			// Backend error codes (refIdRequired, objectUrnAlreadyExists) have
			// message keys; genuine sentences pass through unchanged.
			createError = safeTranslate(error instanceof Error ? error.message : String(error));
		} finally {
			busy = false;
		}
	}
</script>

<!-- Hosts without a reference catalog (store errored) hide the whole row —
     unless the node already carries links, which stay visible/detachable. -->
{#if $catalogStore?.status !== 'error' || current.length > 0}
	<div class="px-4 py-2 border-b border-surface-100-900">
		<div class="flex flex-wrap items-center gap-1">
			<span class="text-xs text-surface-600-400 mr-2">
				{isControl ? m.builderReferenceControlsLabel() : m.builderThreatsLabel()}
			</span>
			{#each current as urn (urn)}
				<span
					class="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border bg-blue-100 border-blue-300 text-blue-700"
					title={urn}
				>
					{labelFor(urn)}
					<button
						type="button"
						class="hover:text-red-600 transition-colors"
						title={m.remove()}
						onclick={() => detach(urn)}
					>
						<i class="fa-solid fa-xmark"></i>
					</button>
				</span>
			{/each}
			{#if $catalogStore?.status !== 'error'}
				<button
					type="button"
					class="text-xs px-2 py-0.5 rounded-full border border-dashed border-surface-300-700 text-surface-500 hover:border-blue-400 hover:text-blue-600 transition-colors"
					disabled={!catalogReady}
					onclick={() => (open = !open)}
				>
					+ {isControl ? m.addReferenceControl() : m.addThreat()}
				</button>
			{/if}
		</div>

		{#if open && catalogReady}
			<div class="mt-2 border border-surface-200-800 rounded p-2 space-y-2 bg-surface-50-950">
				<div class="flex items-center gap-2 text-xs">
					<button
						type="button"
						class="px-2 py-0.5 rounded transition-colors {tab === 'existing'
							? 'bg-blue-100 text-blue-700 font-semibold'
							: 'text-surface-500 hover:text-blue-600'}"
						onclick={() => (tab = 'existing')}
					>
						{m.builderLinkExisting()}
					</button>
					<button
						type="button"
						class="px-2 py-0.5 rounded transition-colors {tab === 'create'
							? 'bg-blue-100 text-blue-700 font-semibold'
							: 'text-surface-500 hover:text-blue-600'}"
						onclick={() => (tab = 'create')}
					>
						{m.builderCreateNew()}
					</button>
					<button
						type="button"
						class="ml-auto text-surface-400 hover:text-surface-600"
						title={m.cancel()}
						onclick={() => (open = false)}
					>
						<i class="fa-solid fa-xmark"></i>
					</button>
				</div>

				{#if tab === 'existing'}
					<input
						type="text"
						class="w-full text-xs px-2 py-1 border border-surface-200-800 rounded focus:border-blue-300 focus:outline-none"
						placeholder={m.search()}
						bind:value={search}
					/>
					<div class="max-h-40 overflow-y-auto divide-y divide-surface-100-900">
						{#each pickable as entry (entry.item.urn)}
							<button
								type="button"
								class="w-full flex items-center gap-2 text-left text-xs px-1 py-1 hover:bg-blue-50 transition-colors"
								onclick={() => attach(entry.item.urn)}
							>
								<span class="font-semibold shrink-0">{entry.item.ref_id ?? ''}</span>
								<span class="text-surface-600-400 truncate"
									>{entry.item.name ?? entry.item.urn}</span
								>
								<span class="ml-auto shrink-0 text-[10px] text-surface-400">
									{entry.source.kind === 'draft' ? '' : entry.source.name}
								</span>
							</button>
						{:else}
							<p class="text-xs text-surface-500 italic px-1 py-1">{m.builderNoCatalogMatches()}</p>
						{/each}
					</div>
					{#if browsableLibraries.length > 0}
						<select
							class="w-full text-xs px-2 py-1 border border-surface-200-800 rounded text-surface-600-400"
							disabled={busy}
							onchange={browseLibrary}
						>
							<option value="">{m.builderBrowseLibrary()}</option>
							{#each browsableLibraries as library (library.library_urn)}
								<option value={library.library_urn}>
									{library.name}{library.provider ? ` — ${library.provider}` : ''}
								</option>
							{/each}
						</select>
						<p class="text-[10px] text-surface-400">{m.builderLinkDependencyHint()}</p>
						{#if browseError}
							<p class="text-[10px] text-red-600">{m.builderCatalogUnavailable()}</p>
						{/if}
					{/if}
				{:else}
					<div class="flex gap-2">
						<input
							type="text"
							class="w-24 text-xs px-2 py-1 border border-surface-200-800 rounded focus:border-blue-300 focus:outline-none"
							placeholder={m.refId()}
							bind:value={createRefId}
						/>
						<input
							type="text"
							class="flex-1 text-xs px-2 py-1 border border-surface-200-800 rounded focus:border-blue-300 focus:outline-none"
							placeholder={m.name()}
							bind:value={createName}
						/>
					</div>
					{#if isControl}
						<div class="flex gap-2">
							<select
								class="flex-1 text-xs px-2 py-1 border border-surface-200-800 rounded text-surface-600-400"
								bind:value={createCategory}
							>
								<option value="">{m.category()}: —</option>
								{#each CATEGORIES as category}
									<option value={category}>{safeTranslate(category)}</option>
								{/each}
							</select>
							<select
								class="flex-1 text-xs px-2 py-1 border border-surface-200-800 rounded text-surface-600-400"
								bind:value={createCsfFunction}
							>
								<option value="">{m.csfFunction()}: —</option>
								{#each CSF_FUNCTIONS as csfFunction}
									<option value={csfFunction}>{safeTranslate(csfFunction)}</option>
								{/each}
							</select>
						</div>
					{/if}
					<textarea
						class="w-full text-xs px-2 py-1 border border-surface-200-800 rounded focus:border-blue-300 focus:outline-none resize-none"
						placeholder={m.description()}
						rows="2"
						bind:value={createDescription}
					></textarea>
					{#if createError}
						<p class="text-xs text-red-600">{createError}</p>
					{/if}
					<div class="flex justify-end">
						<button
							type="button"
							class="text-xs px-3 py-1 rounded bg-blue-600 text-white disabled:opacity-50 hover:bg-blue-700 transition-colors"
							disabled={busy || !createRefId.trim() || !createName.trim()}
							onclick={createNew}
						>
							{m.create()}
						</button>
					</div>
				{/if}
			</div>
		{/if}
	</div>
{/if}
