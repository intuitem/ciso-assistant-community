<script lang="ts">
	import type { PageData } from './$types';
	import { invalidateAll } from '$app/navigation';
	import { goto } from '$lib/utils/breadcrumbs';
	import { pageTitle } from '$lib/utils/stores';

	let { data }: { data: PageData } = $props();
	$pageTitle = 'Preset Editor';

	let busy = $state(false);
	let errorMsg = $state('');
	let showFork = $state(false);
	let blankName = $state('');

	async function callAction(body: any): Promise<any | null> {
		busy = true;
		errorMsg = '';
		try {
			const r = await fetch(`/experimental/preset-editor`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			});
			if (r.status === 204) return null;
			const j = await r.json().catch(() => ({}));
			if (!r.ok) {
				errorMsg = j.detail ?? j.error ?? `Request failed (${r.status})`;
				return null;
			}
			return j;
		} finally {
			busy = false;
		}
	}

	async function createBlank() {
		const name = (blankName || '').trim() || 'Untitled preset';
		const result = await callAction({ action: 'create-blank', name });
		if (!result) return;
		blankName = '';
		goto(`/experimental/preset-editor/${result.id}`, {
			label: result.name,
			breadcrumbAction: 'push'
		});
	}

	async function fork(presetId: string) {
		const result = await callAction({ action: 'duplicate', source_id: presetId });
		if (!result) return;
		showFork = false;
		goto(`/experimental/preset-editor/${result.id}`, {
			label: result.name,
			breadcrumbAction: 'push'
		});
	}

	async function remove(presetId: string, name: string) {
		if (!confirm(`Delete preset "${name}"? This cannot be undone.`)) return;
		await callAction({ action: 'delete', id: presetId });
		await invalidateAll();
	}

	function fmtDate(d: string | undefined): string {
		if (!d) return '—';
		try {
			return new Date(d).toLocaleString();
		} catch {
			return d;
		}
	}
</script>

<div class="flex flex-col gap-6 p-4 max-w-5xl mx-auto">
	<header class="flex items-start justify-between gap-3">
		<div>
			<h1 class="text-2xl font-semibold">Preset Editor</h1>
			<p class="text-sm text-gray-600 mt-1">
				Create and edit user-authored presets. Library-backed presets are read-only — fork one to
				start from.
			</p>
		</div>
	</header>

	{#if errorMsg}
		<div class="bg-red-50 border border-red-300 text-red-800 p-3 rounded text-sm">
			{errorMsg}
		</div>
	{/if}

	<section class="bg-white rounded shadow-sm p-4">
		<h2 class="font-semibold mb-2">Start something new</h2>
		<div class="flex flex-col md:flex-row gap-3 md:items-end">
			<label class="flex flex-col text-sm flex-1">
				<span class="text-gray-700 mb-1">Name (optional)</span>
				<input
					class="input"
					type="text"
					bind:value={blankName}
					placeholder="Untitled preset"
					disabled={busy}
				/>
			</label>
			<button
				type="button"
				class="btn variant-filled-primary"
				onclick={createBlank}
				disabled={busy}
			>
				<i class="fa-solid fa-plus mr-1"></i> Create blank preset
			</button>
			<button
				type="button"
				class="btn variant-soft-secondary"
				onclick={() => (showFork = !showFork)}
				disabled={busy}
			>
				<i class="fa-solid fa-code-fork mr-1"></i>
				{showFork ? 'Hide library presets' : 'Fork from library'}
			</button>
		</div>
	</section>

	{#if showFork}
		<section class="bg-white rounded shadow-sm p-4">
			<h2 class="font-semibold mb-3">Fork from a library preset</h2>
			{#if data.libraryPresets.length === 0}
				<p class="text-sm text-gray-500">No library presets loaded.</p>
			{:else}
				<div class="grid grid-cols-1 md:grid-cols-2 gap-2">
					{#each data.libraryPresets as p (p.id)}
						<div class="border rounded p-3 flex items-start justify-between gap-2">
							<div class="flex-1">
								<p class="font-medium text-sm">{p.name}</p>
								<p class="text-xs text-gray-500 mt-0.5">v{p.version} · {p.urn}</p>
								{#if p.description}
									<p class="text-xs text-gray-700 mt-1 line-clamp-2">{p.description}</p>
								{/if}
							</div>
							<button
								type="button"
								class="btn btn-sm variant-soft"
								onclick={() => fork(p.id)}
								disabled={busy}
							>
								Fork
							</button>
						</div>
					{/each}
				</div>
			{/if}
		</section>
	{/if}

	<section class="bg-white rounded shadow-sm p-4">
		<h2 class="font-semibold mb-3">Your presets</h2>
		{#if data.userAuthored.length === 0}
			<div class="text-sm text-gray-500 py-6 text-center">
				No user-authored presets yet. Create a blank one or fork a library preset above.
			</div>
		{:else}
			<table class="w-full text-sm">
				<thead class="text-xs text-gray-600 border-b">
					<tr>
						<th class="text-left py-2 px-2">Name</th>
						<th class="text-left py-2 px-2">Version</th>
						<th class="text-left py-2 px-2">Updated</th>
						<th class="text-right py-2 px-2">Actions</th>
					</tr>
				</thead>
				<tbody>
					{#each data.userAuthored as p (p.id)}
						<tr class="border-b last:border-b-0 hover:bg-gray-50">
							<td class="py-2 px-2">
								<a
									href="/experimental/preset-editor/{p.id}"
									class="text-violet-700 hover:underline font-medium"
								>
									{p.name}
								</a>
								{#if p.description}
									<p class="text-xs text-gray-500 line-clamp-1">{p.description}</p>
								{/if}
							</td>
							<td class="py-2 px-2 text-gray-700">v{p.version}</td>
							<td class="py-2 px-2 text-gray-500 text-xs">{fmtDate(p.updated_at)}</td>
							<td class="py-2 px-2 text-right">
								<a href="/experimental/preset-editor/{p.id}" class="btn btn-sm variant-soft">
									Open
								</a>
								<button
									type="button"
									class="btn btn-sm variant-soft-error"
									onclick={() => remove(p.id, p.name)}
									disabled={busy}
								>
									Delete
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</section>
</div>
