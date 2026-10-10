<script lang="ts">
	import TTPMatrix from '$lib/components/TTPMatrix/TTPMatrix.svelte';
	import type { MatrixCell } from '$lib/components/TTPMatrix/TTPMatrix.svelte';
	import { m } from '$paraglide/messages';
	import { untrack } from 'svelte';
	import ViewSwitch from '../ViewSwitch.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	const matrix = $derived(data.matrix);
	const threatModel = $derived(data.threatModel);

	let selected = $state(new Set<string>(data.matrix.selected ?? []));
	let saved = $state(new Set<string>(data.matrix.selected ?? []));

	// the component is reused when navigating between threat models, so the
	// selection must follow the loaded data rather than stick from the first one
	$effect(() => {
		const fresh = new Set<string>(data.matrix.selected ?? []);
		untrack(() => {
			selected = fresh;
			saved = new Set(fresh);
			errorMessage = '';
		});
	});
	let saving = $state(false);
	let errorMessage = $state('');

	const dirty = $derived(
		selected.size !== saved.size || [...selected].some((id) => !saved.has(id))
	);

	// keyed per cell: the same technique in two tactic columns is two selections
	function toggle(cell: MatrixCell, column: { id: string }) {
		const key = `${cell.id}:${column.id}`;
		const next = new Set(selected);
		next.has(key) ? next.delete(key) : next.add(key);
		selected = next;
	}

	async function save() {
		saving = true;
		errorMessage = '';
		// snapshot: what comes back confirms this payload, not later edits
		const submitted = new Set(selected);
		try {
			const res = await fetch(`/threat-models/${threatModel.id}/set-techniques`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					selections: [...submitted].map((key) => {
						const [technique, tactic] = key.split(':');
						return { technique, tactic };
					})
				})
			});
			const payload = await res.json().catch(() => ({}));
			if (res.ok) {
				saved = submitted;
			} else {
				errorMessage = (payload.errors ?? [m.anErrorOccurred()]).join(' ');
			}
		} catch {
			errorMessage = m.anErrorOccurred();
		} finally {
			saving = false;
		}
	}
</script>

<div class="p-4 space-y-4">
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div class="space-y-1">
			<h1 class="h3">{threatModel.name}</h1>
			<p class="text-sm text-surface-600-400">{matrix.catalog.name}</p>
		</div>
		<div class="flex items-center gap-3">
			<ViewSwitch threatModelId={threatModel.id} active="select" />
			<span class="text-sm text-surface-600-400">
				{selected.size}
				{m.techniquesSelected()}
			</span>
			<a class="btn preset-tonal-surface" href="/threat-models/{threatModel.id}">{m.details()}</a>
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
