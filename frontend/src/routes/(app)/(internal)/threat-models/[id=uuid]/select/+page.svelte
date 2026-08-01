<script lang="ts">
	import TTPMatrix from '$lib/components/TTPMatrix/TTPMatrix.svelte';
	import type { MatrixCell } from '$lib/components/TTPMatrix/TTPMatrix.svelte';
	import { m } from '$paraglide/messages';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const matrix = $derived(data.matrix);
	const threatModel = $derived(data.threatModel);

	let selected = $state(new Set<string>(data.matrix.selected ?? []));
	let saved = $state(new Set<string>(data.matrix.selected ?? []));
	let saving = $state(false);
	let errorMessage = $state('');

	const dirty = $derived(
		selected.size !== saved.size || [...selected].some((id) => !saved.has(id))
	);

	function toggle(cell: MatrixCell) {
		const next = new Set(selected);
		next.has(cell.id) ? next.delete(cell.id) : next.add(cell.id);
		selected = next;
	}

	async function save() {
		saving = true;
		errorMessage = '';
		const res = await fetch(`/threat-models/${threatModel.id}/set-techniques`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ technique_ids: [...selected] })
		});
		const payload = await res.json();
		if (res.ok) {
			saved = new Set(selected);
		} else {
			errorMessage = (payload.errors ?? [m.errorOccurred()]).join(' ');
		}
		saving = false;
	}
</script>

<div class="p-4 space-y-4">
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div class="space-y-1">
			<h1 class="h3">{threatModel.name}</h1>
			<p class="text-sm text-surface-600-400">{matrix.catalog.name}</p>
		</div>
		<div class="flex items-center gap-3">
			<span class="text-sm text-surface-600-400">
				{selected.size}
				{m.techniquesSelected()}
			</span>
			<a class="btn preset-tonal-surface" href="/threat-models/{threatModel.id}">{m.cancel()}</a>
			<button
				type="button"
				class="btn preset-filled-primary-500"
				disabled={!dirty || saving}
				onclick={save}
			>
				{saving ? m.saving() : m.save()}
			</button>
		</div>
	</div>

	{#if errorMessage}
		<aside class="card preset-tonal-error p-3 text-sm">{errorMessage}</aside>
	{/if}

	{#if matrix.columns.length}
		<TTPMatrix
			columns={matrix.columns}
			cells={matrix.cells}
			facets={matrix.facets}
			selectable
			{selected}
			onToggle={toggle}
		/>
	{:else}
		<p class="text-surface-600-400">{m.noTTPCatalogMatrix()}</p>
	{/if}
</div>
