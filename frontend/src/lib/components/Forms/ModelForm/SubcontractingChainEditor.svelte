<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';

	interface ChainRow {
		subcontractor: string;
		recipient: string | null;
	}

	interface TreeNode {
		entityId: string;
		label: string;
		depth: number;
		children: TreeNode[];
	}

	interface Props {
		form: SuperValidated<any>;
		/** Current direct provider (rank 1, implicit). Excluded from the picker. */
		directProviderId?: string | null;
	}

	let { form, directProviderId = null }: Props = $props();

	const formData = form.form;

	let chain = $state<ChainRow[]>(
		(($formData as any).subcontracting_chain ?? []).map((r: any) => ({
			subcontractor: r.subcontractor ?? '',
			recipient: r.recipient ?? null
		}))
	);

	let entityLabels = $state<Map<string, string>>(new Map());
	let addingChildOf = $state<string | null>(null);
	let confirmingRemove = $state<string | null>(null);

	// Picker state (per-node, only one open at a time).
	const pickerField = '__subcontractor_picker';
	let pickerCached = $state<string[] | undefined>([]);
	let pickerCachedOptions = $state<any[] | undefined>([]);

	let directProviderLabel = $derived(
		directProviderId ? (entityLabels.get(directProviderId) ?? null) : null
	);

	// --- Tree building (depth computed from recipient pointers) ---

	function buildTree(
		rows: ChainRow[],
		providerId: string | null,
		labels: Map<string, string>
	): TreeNode {
		const rootId = providerId ?? '__no_provider__';
		const root: TreeNode = {
			entityId: rootId,
			label: labels.get(providerId ?? '') ?? '',
			depth: 1,
			children: []
		};

		const nodeMap = new Map<string, TreeNode>();
		nodeMap.set(rootId, root);

		// Create nodes (depth assigned later via parent linkage).
		for (const row of rows) {
			nodeMap.set(row.subcontractor, {
				entityId: row.subcontractor,
				label: labels.get(row.subcontractor) ?? row.subcontractor,
				depth: 0,
				children: []
			});
		}

		// Link children to parents.
		for (const row of rows) {
			const node = nodeMap.get(row.subcontractor)!;
			const parentId = row.recipient ?? rootId;
			const parent = nodeMap.get(parentId);
			if (parent) {
				parent.children.push(node);
			} else {
				root.children.push(node);
			}
		}

		// Assign depth via DFS.
		function assignDepth(node: TreeNode, d: number) {
			node.depth = d;
			for (const child of node.children) assignDepth(child, d + 1);
		}
		assignDepth(root, 1);

		return root;
	}

	let tree = $derived(buildTree(chain, directProviderId, entityLabels));

	// --- Mutations ---

	function commit(next: ChainRow[]) {
		chain = next;
		($formData as any).subcontracting_chain = chain;
	}

	function onPickerChange(parentEntityId: string, value: unknown) {
		const id = Array.isArray(value) ? value[0] : value;
		if (!id || typeof id !== 'string') return;
		if (directProviderId === id) return;
		if (chain.some((r) => r.subcontractor === id)) return;

		const picked = (pickerCachedOptions ?? []).find((o: any) => o?.value === id);
		if (picked?.label) entityLabels.set(id, picked.label);

		const recipient = parentEntityId === directProviderId ? null : parentEntityId;

		commit([...chain, { subcontractor: id, recipient }]);
		addingChildOf = null;
	}

	function collectSubtreeIds(node: TreeNode): Set<string> {
		const ids = new Set<string>();
		function walk(n: TreeNode) {
			ids.add(n.entityId);
			for (const child of n.children) walk(child);
		}
		walk(node);
		return ids;
	}

	function findNode(node: TreeNode, entityId: string): TreeNode | null {
		if (node.entityId === entityId) return node;
		for (const child of node.children) {
			const found = findNode(child, entityId);
			if (found) return found;
		}
		return null;
	}

	function removeNode(entityId: string) {
		const target = findNode(tree, entityId);
		if (!target) return;
		const toRemove = collectSubtreeIds(target);
		commit(chain.filter((row) => !toRemove.has(row.subcontractor)));
		confirmingRemove = null;
	}

	function handleRemoveClick(entityId: string, childCount: number) {
		if (childCount === 0) {
			removeNode(entityId);
		} else {
			confirmingRemove = entityId;
		}
	}

	function displayLabel(entityId: string): string {
		return entityLabels.get(entityId) ?? entityId;
	}

	function tierLabel(depth: number): string {
		if (depth === 2) return m.subcontractor();
		return `${m.subcontractor()} (${m.subcontractingTier({ n: depth - 1 })})`;
	}

	function subtreeCount(node: TreeNode): number {
		let count = 0;
		for (const child of node.children) {
			count += 1 + subtreeCount(child);
		}
		return count;
	}

	onMount(async () => {
		try {
			const res = await fetch('/entities?is_active=true');
			if (!res.ok) return;
			const data = await res.json();
			const results = Array.isArray(data?.results) ? data.results : data;
			const next = new Map(entityLabels);
			for (const e of results) {
				next.set(e.id as string, (e.name ?? e.str ?? e.id) as string);
			}
			entityLabels = next;
		} catch {
			// Labels unavailable — rows render with the raw id. Non-fatal.
		}
	});
</script>

{#snippet nodeCard(node: TreeNode, isRoot: boolean)}
	<div
		class="flex items-center gap-3 rounded border p-3 {isRoot
			? 'border-surface-300 bg-surface-100'
			: 'border-surface-200'}"
		data-testid={isRoot ? 'chain-direct-provider' : 'chain-row'}
	>
		<div
			class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full {isRoot
				? 'bg-primary-500 text-white'
				: 'bg-surface-300 text-surface-700'}"
		>
			<i class="fa-solid {isRoot ? 'fa-building' : 'fa-sitemap'}" aria-hidden="true"></i>
		</div>
		<div class="flex-1">
			<div class="text-xs font-semibold tracking-wide text-surface-600 uppercase">
				{#if isRoot}
					{m.subcontractingDirectProvider()}
				{:else}
					{tierLabel(node.depth)}
				{/if}
			</div>
			<div class="text-sm font-medium">
				{#if isRoot}
					{directProviderLabel ?? m.subcontractingDirectProviderUnset()}
				{:else}
					{displayLabel(node.entityId)}
				{/if}
			</div>
		</div>
		<div class="flex items-center gap-1">
			{#if isRoot}
				<span class="text-xs text-surface-500" title={m.subcontractingRank1ImplicitHelp()}>
					<i class="fa-solid fa-lock" aria-hidden="true"></i>
				</span>
			{/if}
			{#if directProviderId}
				<button
					type="button"
					class="btn btn-sm preset-tonal"
					onclick={() => {
						addingChildOf = addingChildOf === node.entityId ? null : node.entityId;
						confirmingRemove = null;
					}}
					aria-label={m.addSubcontractorTo({ entity: displayLabel(node.entityId) })}
					title={m.addSubcontractorTo({ entity: displayLabel(node.entityId) })}
				>
					<i class="fa-solid fa-plus" aria-hidden="true"></i>
				</button>
			{/if}
			{#if !isRoot}
				{#if confirmingRemove === node.entityId}
					<!-- inline confirmation for non-leaf removal -->
					<div class="flex items-center gap-1">
						<button
							type="button"
							class="btn btn-sm preset-filled-error-500"
							onclick={() => removeNode(node.entityId)}
						>
							{m.confirm()}
						</button>
						<button
							type="button"
							class="btn btn-sm preset-tonal"
							onclick={() => (confirmingRemove = null)}
						>
							{m.cancel()}
						</button>
					</div>
				{:else}
					<button
						type="button"
						class="btn btn-sm preset-tonal-error"
						onclick={() => handleRemoveClick(node.entityId, node.children.length)}
						aria-label={m.remove()}
					>
						<i class="fa-solid fa-trash" aria-hidden="true"></i>
					</button>
				{/if}
			{/if}
		</div>
	</div>

	<!-- Subtree removal warning text -->
	{#if confirmingRemove === node.entityId}
		<p class="mt-1 text-xs text-error-500">
			{m.removeSubtreeConfirm({ n: subtreeCount(node) })}
		</p>
	{/if}

	<!-- Inline picker when adding a child to this node -->
	{#if addingChildOf === node.entityId}
		<div class="mt-2 rounded border border-dashed border-surface-300 p-3">
			<div class="mb-2 text-xs font-semibold tracking-wide text-surface-600 uppercase">
				{m.addSubcontractorTo({ entity: displayLabel(node.entityId) })}
			</div>
			{#key chain.length + '-' + node.entityId}
				<AutocompleteSelect
					{form}
					field={pickerField}
					optionsEndpoint="entities"
					optionsExtraFields={[['folder', 'str']]}
					optionsSelf={directProviderId ? { id: directProviderId } : null}
					bind:cachedValue={pickerCached}
					bind:cachedOptions={pickerCachedOptions}
					onChange={(value) => onPickerChange(node.entityId, value)}
					label=""
					placeholder={m.pickAnEntity()}
					nullable
				/>
			{/key}
		</div>
	{/if}

	<!-- Children -->
	{#if node.children.length > 0}
		<div class="ml-6 border-l-2 border-surface-300 pl-4 mt-2 space-y-2">
			{#each node.children as child (child.entityId)}
				{@render nodeCard(child, false)}
			{/each}
		</div>
	{/if}
{/snippet}

<div class="space-y-3">
	<p class="text-sm text-surface-500">{m.subcontractingChainHelpText()}</p>

	{@render nodeCard(tree, true)}

	<!-- Hidden input: serialized chain for form-action POST/PATCH flows. -->
	<input type="hidden" name="subcontracting_chain" value={JSON.stringify(chain)} />
</div>
