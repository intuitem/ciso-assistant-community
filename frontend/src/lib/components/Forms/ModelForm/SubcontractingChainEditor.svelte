<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { onMount } from 'svelte';
	import { m } from '$paraglide/messages';

	interface ChainRow {
		subcontractor: string;
		rank: number;
	}

	interface Props {
		form: SuperValidated<any>;
		/** Current direct provider (rank 1, implicit). Excluded from the picker. */
		directProviderId?: string | null;
	}

	let { form, directProviderId = null }: Props = $props();

	const formData = form.form;

	// Source of truth: ordered array. Position defines rank (position 0 = rank 2, ...).
	// Stored `rank` field is derived; we assign it from position on every commit.
	let chain = $state<ChainRow[]>(
		renumber((($formData as any).subcontracting_chain ?? []) as ChainRow[])
	);

	// Label lookup for rendering chain rows AND the direct provider card.
	// Populated from two sources:
	//   1. one-shot fetch on mount of all viewable entities,
	//   2. the cachedOptions binding from AutocompleteSelect when the user picks.
	let entityLabels = $state<Map<string, string>>(new Map());

	// Resolve the direct provider's label from the same lookup. Single source
	// of truth, avoids depending on the parent form's initialData shape.
	let directProviderLabel = $derived(
		directProviderId ? (entityLabels.get(directProviderId) ?? null) : null
	);

	// Picker state — AutocompleteSelect is form-bound. Use a synthetic field
	// name that doesn't collide with the Solution schema; superforms creates
	// it lazily and we never submit it. The picker is force-remounted via
	// `{#key chain.length}` after each successful append, which clears its
	// internal `selected` state — simpler than trying to drive the component
	// to clear itself through props.
	const pickerField = '__subcontractor_picker';
	let pickerCached = $state<string[] | undefined>([]);
	let pickerCachedOptions = $state<any[] | undefined>([]);

	function renumber(rows: ChainRow[]): ChainRow[] {
		return rows.map((r, i) => ({ subcontractor: r.subcontractor ?? '', rank: i + 2 }));
	}

	function commit(next: ChainRow[]) {
		chain = renumber(next);
		($formData as any).subcontracting_chain = chain;
	}

	function onPickerChange(value: unknown) {
		const id = Array.isArray(value) ? value[0] : value;
		if (!id || typeof id !== 'string') return;

		// Guard: direct provider is excluded via optionsSelf but double-check.
		if (directProviderId === id) return;
		// Duplicate guard: silently ignore — the picker remounts on commit
		// so the stale selection is cleared either way.
		if (chain.some((r) => r.subcontractor === id)) return;

		// Capture the label from AutocompleteSelect's cachedOptions for display.
		const picked = (pickerCachedOptions ?? []).find((o: any) => o?.value === id);
		if (picked?.label) entityLabels.set(id, picked.label);

		// commit() bumps chain.length, which triggers `{#key chain.length}` to
		// remount AutocompleteSelect with a fresh empty selection.
		commit([...chain, { subcontractor: id, rank: chain.length + 2 }]);
	}

	function removeRow(index: number) {
		const next = chain.slice();
		next.splice(index, 1);
		commit(next);
	}

	function moveUp(index: number) {
		if (index === 0) return;
		const next = chain.slice();
		[next[index - 1], next[index]] = [next[index], next[index - 1]];
		commit(next);
	}

	function moveDown(index: number) {
		if (index === chain.length - 1) return;
		const next = chain.slice();
		[next[index + 1], next[index]] = [next[index], next[index + 1]];
		commit(next);
	}

	function displayLabel(entityId: string): string {
		return entityLabels.get(entityId) ?? entityId;
	}

	function tierLabel(rank: number): string {
		if (rank === 2) return m.subcontractor();
		return `${m.subcontractor()} (${m.subcontractingTier({ n: rank - 1 })})`;
	}

	// One-shot label fetch on mount. Always runs — populates labels for the
	// direct provider card AND any chain rows loaded with the form. Cheap
	// (one request) and we read folder-scoped results via the existing
	// /entities endpoint.
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

<div class="space-y-3">
	<p class="text-sm text-surface-500">{m.subcontractingChainHelpText()}</p>

	<!-- Locked "Direct provider" card (rank 1, implicit) -->
	<div
		class="flex items-center gap-3 rounded border border-surface-300 bg-surface-100 p-3"
		data-testid="chain-direct-provider"
	>
		<div class="flex h-8 w-8 items-center justify-center rounded-full bg-primary-500 text-white">
			<i class="fa-solid fa-building" aria-hidden="true"></i>
		</div>
		<div class="flex-1">
			<div class="text-xs font-semibold tracking-wide text-surface-600 uppercase">
				{m.subcontractingDirectProvider()}
			</div>
			<div class="text-sm font-medium">
				{directProviderLabel ?? m.subcontractingDirectProviderUnset()}
			</div>
		</div>
		<span class="text-xs text-surface-500" title={m.subcontractingRank1ImplicitHelp()}>
			<i class="fa-solid fa-lock" aria-hidden="true"></i>
		</span>
	</div>

	<!-- Chain rows: static cards with reorder/remove controls. -->
	{#each chain as row, index (index)}
		<div
			class="flex items-center gap-3 rounded border border-surface-200 p-3"
			data-testid="chain-row"
		>
			<div
				class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-300 text-surface-700"
			>
				<i class="fa-solid fa-sitemap" aria-hidden="true"></i>
			</div>
			<div class="flex-1">
				<div class="text-xs font-semibold tracking-wide text-surface-600 uppercase">
					{tierLabel(row.rank)}
				</div>
				<div class="text-sm font-medium">{displayLabel(row.subcontractor)}</div>
			</div>
			<div class="flex flex-col gap-1">
				<button
					type="button"
					class="btn btn-sm preset-tonal"
					disabled={index === 0}
					onclick={() => moveUp(index)}
					aria-label={m.moveUp()}
				>
					<i class="fa-solid fa-arrow-up" aria-hidden="true"></i>
				</button>
				<button
					type="button"
					class="btn btn-sm preset-tonal"
					disabled={index === chain.length - 1}
					onclick={() => moveDown(index)}
					aria-label={m.moveDown()}
				>
					<i class="fa-solid fa-arrow-down" aria-hidden="true"></i>
				</button>
				<button
					type="button"
					class="btn btn-sm preset-tonal-error"
					onclick={() => removeRow(index)}
					aria-label={m.remove()}
				>
					<i class="fa-solid fa-trash" aria-hidden="true"></i>
				</button>
			</div>
		</div>
	{/each}

	<!-- One picker that appends to the chain on select. AutocompleteSelect does
	     the fetching, searching, keyboard nav, and folder-scoped RBAC. The
	     direct provider is excluded via `optionsSelf`. The whole component is
	     remounted on every chain change via `{#key chain.length}` so the
	     internal selection state resets immediately after a pick. -->
	<div class="rounded border border-dashed border-surface-300 p-3">
		<div class="mb-2 text-xs font-semibold tracking-wide text-surface-600 uppercase">
			{m.addSubcontractor()}
		</div>
		{#key chain.length}
			<AutocompleteSelect
				{form}
				field={pickerField}
				optionsEndpoint="entities"
				optionsExtraFields={[['folder', 'str']]}
				optionsSelf={directProviderId ? { id: directProviderId } : null}
				bind:cachedValue={pickerCached}
				bind:cachedOptions={pickerCachedOptions}
				onChange={onPickerChange}
				label=""
				placeholder={m.pickAnEntity()}
				nullable
			/>
		{/key}
	</div>

	<!-- Hidden input: serialized chain for form-action POST/PATCH flows. -->
	<input type="hidden" name="subcontracting_chain" value={JSON.stringify(chain)} />
</div>
