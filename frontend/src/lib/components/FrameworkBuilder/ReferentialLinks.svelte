<script lang="ts">
	import {
		getBuilderContext,
		getReferentialCatalogContext,
		slugifyFrameworkName,
		type BuilderNode,
		type InlineReferential,
		type ReferentialCatalogEntry
	} from './builder-state';
	import { m } from '$paraglide/messages';

	interface Props {
		node: BuilderNode;
		kind: 'reference_controls' | 'threats';
	}

	let { node, kind }: Props = $props();

	const builder = getBuilderContext();
	const { framework: frameworkStore } = builder;
	const catalog = getReferentialCatalogContext();

	const isControl = kind === 'reference_controls';
	const inlineKey = isControl ? 'inline_reference_controls' : 'inline_threats';
	const urnType = isControl ? 'reference_control' : 'threat';
	// Reference-control categories, matching ReferenceControl.CATEGORY on the backend.
	const CATEGORIES = ['policy', 'process', 'technical', 'physical', 'procedure'];

	let adding = $state(false);
	let tab: 'existing' | 'inline' = $state('existing');
	let search = $state('');
	let newRefId = $state('');
	let newName = $state('');
	let newCategory = $state('');

	const currentUrns = $derived((node.node[kind] ?? []) as string[]);
	const catalogEntries = $derived(
		isControl ? catalog.referenceControls : catalog.threats
	) as ReferentialCatalogEntry[];
	const inlineEntries = $derived(($frameworkStore[inlineKey] ?? []) as InlineReferential[]);

	// urn -> display label, from both the server catalog and locally-defined ones.
	const labelByUrn = $derived.by(() => {
		const map = new Map<string, string>();
		for (const e of catalogEntries) {
			if (e.urn) map.set(e.urn, e.ref_id ? `${e.ref_id} — ${e.name ?? ''}` : (e.name ?? e.urn));
		}
		for (const e of inlineEntries) {
			if (e.urn) map.set(e.urn, e.ref_id ? `${e.ref_id} — ${e.name ?? ''}` : (e.name ?? e.urn));
		}
		return map;
	});

	const linkableEntries = $derived.by(() => {
		const linked = new Set(currentUrns);
		const term = search.trim().toLowerCase();
		return catalogEntries
			.filter((e) => e.urn && !linked.has(e.urn))
			.filter(
				(e) =>
					!term ||
					(e.name ?? '').toLowerCase().includes(term) ||
					(e.ref_id ?? '').toLowerCase().includes(term) ||
					e.urn.toLowerCase().includes(term)
			)
			.slice(0, 50);
	});

	function addUrn(urn: string) {
		if (currentUrns.includes(urn)) return;
		builder.updateNode(node.node.id, { [kind]: [...currentUrns, urn] });
	}

	function removeUrn(urn: string) {
		builder.updateNode(node.node.id, { [kind]: currentUrns.filter((u) => u !== urn) });
	}

	function frameworkSlug(): string {
		const fw = $frameworkStore;
		return fw.ref_id && fw.ref_id.length > 0 ? fw.ref_id : slugifyFrameworkName(fw.name, fw.id);
	}

	function createInline() {
		const refId = newRefId.trim();
		if (!refId) return;
		const ns = $frameworkStore.urn_namespace || 'custom';
		const suffix = refId.toLowerCase().replace(/[^a-z0-9._-]+/g, '-');
		const urn = `urn:${ns}:risk:${urnType}:${frameworkSlug()}:${suffix}`;
		const entry: InlineReferential = {
			id: crypto.randomUUID(),
			urn,
			ref_id: refId,
			name: newName.trim() || null,
			description: null,
			annotation: null,
			translations: null,
			...(isControl ? { category: newCategory || null, csf_function: null } : {})
		};
		builder.updateFramework({ [inlineKey]: [...inlineEntries, entry] });
		addUrn(urn);
		newRefId = '';
		newName = '';
		newCategory = '';
		adding = false;
	}
</script>

<div class="px-4 py-2 border-b border-gray-100">
	<div class="flex items-center flex-wrap gap-1">
		<span class="text-xs text-gray-500 mr-1">
			{isControl ? m.builderReferenceControlsLabel() : m.builderThreatsLabel()}
		</span>
		{#each currentUrns as urn (urn)}
			<span
				class="inline-flex items-center text-xs px-2 py-0.5 rounded-full border bg-blue-50 border-blue-200 text-blue-700"
			>
				{labelByUrn.get(urn) ?? urn}
				<button
					type="button"
					class="ml-1 text-blue-400 hover:text-blue-700"
					aria-label={m.remove()}
					onclick={() => removeUrn(urn)}
				>
					<i class="fa-solid fa-xmark"></i>
				</button>
			</span>
		{/each}
		<button
			type="button"
			class="text-xs px-2 py-0.5 rounded-full border border-dashed border-gray-300 text-gray-400 hover:text-gray-600 hover:border-gray-400"
			onclick={() => (adding = !adding)}
		>
			<i class="fa-solid fa-plus mr-1"></i>{isControl
				? m.builderAddReferenceControl()
				: m.builderAddThreat()}
		</button>
	</div>

	{#if adding}
		<div class="mt-2 p-2 border border-gray-200 rounded bg-gray-50">
			<div class="flex gap-2 mb-2 text-xs">
				<button
					type="button"
					class="px-2 py-0.5 rounded {tab === 'existing'
						? 'bg-blue-100 text-blue-700'
						: 'text-gray-500'}"
					onclick={() => (tab = 'existing')}
				>
					{m.builderLinkExisting()}
				</button>
				<button
					type="button"
					class="px-2 py-0.5 rounded {tab === 'inline'
						? 'bg-blue-100 text-blue-700'
						: 'text-gray-500'}"
					onclick={() => (tab = 'inline')}
				>
					{m.builderDefineInline()}
				</button>
			</div>

			{#if tab === 'existing'}
				<input
					type="text"
					class="w-full text-xs px-2 py-1 border border-gray-200 rounded mb-1"
					placeholder={m.search()}
					bind:value={search}
				/>
				<ul class="max-h-40 overflow-y-auto">
					{#each linkableEntries as entry (entry.urn)}
						<li>
							<button
								type="button"
								class="w-full text-left text-xs px-2 py-1 hover:bg-blue-50 rounded"
								onclick={() => addUrn(entry.urn)}
							>
								<span class="font-medium">{entry.ref_id ?? entry.name ?? entry.urn}</span>
								{#if entry.ref_id && entry.name}<span class="text-gray-500">
										— {entry.name}</span
									>{/if}
							</button>
						</li>
					{:else}
						<li class="text-xs text-gray-400 px-2 py-1">{m.builderNoCatalogMatches()}</li>
					{/each}
				</ul>
			{:else}
				<div class="flex flex-wrap gap-1 items-center">
					<input
						type="text"
						class="text-xs px-2 py-1 border border-gray-200 rounded w-24"
						placeholder={m.refId()}
						bind:value={newRefId}
					/>
					<input
						type="text"
						class="text-xs px-2 py-1 border border-gray-200 rounded flex-1 min-w-32"
						placeholder={m.name()}
						bind:value={newName}
					/>
					{#if isControl}
						<select
							class="text-xs px-2 py-1 border border-gray-200 rounded"
							bind:value={newCategory}
						>
							<option value="">—</option>
							{#each CATEGORIES as cat}
								<option value={cat}>{cat}</option>
							{/each}
						</select>
					{/if}
					<button
						type="button"
						class="text-xs px-2 py-1 rounded bg-blue-600 text-white disabled:opacity-50"
						disabled={!newRefId.trim()}
						onclick={createInline}
					>
						{m.create()}
					</button>
				</div>
			{/if}
		</div>
	{/if}
</div>
