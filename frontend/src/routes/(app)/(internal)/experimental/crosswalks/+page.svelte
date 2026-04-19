<script lang="ts">
	import { goto } from '$app/navigation';
	import { pageTitle } from '$lib/utils/stores';

	$pageTitle = 'Crosswalks';

	let { data } = $props();
	let crosswalks: any[] = $state(data.crosswalks ?? []);
	const frameworks: any[] = data.frameworks ?? [];
	const librarySources: any[] = data.librarySources ?? [];
	let cloneBusyId = $state<string | null>(null);
	let cloneError = $state('');

	let sourceFrameworkId = $state('');
	let targetFrameworkId = $state('');
	let name = $state('');
	let description = $state('');
	let creating = $state(false);
	let errorMessage = $state('');

	const statusBadge: Record<string, string> = {
		draft: 'bg-gray-200 text-gray-700',
		generating: 'bg-blue-100 text-blue-700',
		ready: 'bg-green-100 text-green-700',
		reviewed: 'bg-emerald-100 text-emerald-800',
		failed: 'bg-red-100 text-red-700'
	};

	async function createCrosswalk() {
		errorMessage = '';
		if (!sourceFrameworkId || !targetFrameworkId) {
			errorMessage = 'Pick both a source and target framework.';
			return;
		}
		if (sourceFrameworkId === targetFrameworkId) {
			errorMessage = 'Source and target must differ.';
			return;
		}
		creating = true;
		try {
			const src = frameworks.find((f: any) => f.id === sourceFrameworkId);
			const tgt = frameworks.find((f: any) => f.id === targetFrameworkId);
			const payload = {
				name: name || `${src?.name ?? 'source'} → ${tgt?.name ?? 'target'}`,
				description,
				source_framework: sourceFrameworkId,
				target_framework: targetFrameworkId
			};
			const res = await fetch('/experimental/crosswalks', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			const body = await res.json();
			if (!res.ok) {
				errorMessage = body?.detail || JSON.stringify(body);
				return;
			}
			goto(`/experimental/crosswalks/${body.id}`);
		} catch (e: any) {
			errorMessage = e.message ?? String(e);
		} finally {
			creating = false;
		}
	}

	async function cloneFromLibrary(source: any) {
		cloneError = '';
		cloneBusyId = `${source.stored_library_id}:${source.set_urn}`;
		try {
			const res = await fetch('/experimental/crosswalks/clone-from', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					stored_library_id: source.stored_library_id,
					set_urn: source.set_urn
				})
			});
			const body = await res.json();
			if (!res.ok) {
				cloneError = body?.error || body?.detail || JSON.stringify(body);
				return;
			}
			goto(`/experimental/crosswalks/${body.id}`);
		} catch (e: any) {
			cloneError = e.message ?? String(e);
		} finally {
			cloneBusyId = null;
		}
	}

	async function deleteCrosswalk(id: string) {
		if (!confirm('Delete this crosswalk? This also removes all pair suggestions.')) return;
		const res = await fetch(`/experimental/crosswalks/${id}`, { method: 'DELETE' });
		if (res.ok || res.status === 204) {
			crosswalks = crosswalks.filter((c) => c.id !== id);
		}
	}

	function formatDate(iso: string | null | undefined) {
		if (!iso) return '—';
		try {
			return new Date(iso).toLocaleString();
		} catch {
			return iso;
		}
	}

	// --- Library sources pagination ---
	const PAGE_SIZE = 10;
	let librarySearch = $state('');
	let libraryPage = $state(1);
	let filteredLibrary = $derived(
		(() => {
			const q = librarySearch.trim().toLowerCase();
			if (!q) return librarySources;
			return librarySources.filter((s) => {
				const hay = [s.name, s.source_framework?.name, s.target_framework?.name, s.provider]
					.filter(Boolean)
					.join(' ')
					.toLowerCase();
				return hay.includes(q);
			});
		})()
	);
	let libraryPageCount = $derived(Math.max(1, Math.ceil(filteredLibrary.length / PAGE_SIZE)));
	$effect(() => {
		if (libraryPage > libraryPageCount) libraryPage = libraryPageCount;
	});
	let libraryPageRows = $derived(
		filteredLibrary.slice((libraryPage - 1) * PAGE_SIZE, libraryPage * PAGE_SIZE)
	);
</script>

<div class="space-y-6 p-4">
	<header class="space-y-1">
		<h1 class="text-2xl font-semibold">Crosswalks</h1>
		<p class="text-sm text-gray-500">
			Generate a draft crosswalk between two frameworks using semantic similarity. The engine
			suggests candidate pairs with orientation hints — you make the final call on the relationship
			type.
		</p>
	</header>

	<section class="card p-4 space-y-4">
		<h2 class="text-lg font-semibold">
			<i class="fa-solid fa-plus mr-1"></i> New crosswalk
		</h2>
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
			<div>
				<label class="label" for="src-fw">Source framework</label>
				<select id="src-fw" class="select" bind:value={sourceFrameworkId}>
					<option value="">—</option>
					{#each frameworks as fw}
						<option value={fw.id}>{fw.name}</option>
					{/each}
				</select>
			</div>
			<div>
				<label class="label" for="tgt-fw">Target framework</label>
				<select id="tgt-fw" class="select" bind:value={targetFrameworkId}>
					<option value="">—</option>
					{#each frameworks as fw}
						<option value={fw.id}>{fw.name}</option>
					{/each}
				</select>
			</div>
			<div>
				<label class="label" for="cw-name">Name (optional)</label>
				<input
					id="cw-name"
					class="input"
					type="text"
					bind:value={name}
					placeholder="Auto-generated from framework names"
				/>
			</div>
			<div>
				<label class="label" for="cw-desc">Description (optional)</label>
				<input id="cw-desc" class="input" type="text" bind:value={description} />
			</div>
		</div>
		{#if errorMessage}
			<p class="text-sm text-red-600">{errorMessage}</p>
		{/if}
		<div class="flex justify-end">
			<button
				type="button"
				class="btn bg-primary-500 text-white hover:bg-primary-600 disabled:opacity-50"
				onclick={createCrosswalk}
				disabled={creating}
			>
				{#if creating}
					<i class="fa-solid fa-spinner fa-spin mr-1"></i>
				{:else}
					<i class="fa-solid fa-wand-magic-sparkles mr-1"></i>
				{/if}
				Generate suggestions
			</button>
		</div>
	</section>

	<section class="card p-4">
		<h2 class="text-lg font-semibold mb-3">
			<i class="fa-solid fa-list mr-1"></i> Existing crosswalks
		</h2>
		{#if crosswalks.length === 0}
			<p class="text-sm text-gray-400 py-6 text-center">No crosswalks yet. Create one above.</p>
		{:else}
			<div class="overflow-x-auto">
				<table class="table table-compact w-full">
					<thead>
						<tr>
							<th>Name</th>
							<th>Source</th>
							<th>Target</th>
							<th>Status</th>
							<th>Pairs</th>
							<th>Reviewed</th>
							<th>Generated</th>
							<th class="w-36"></th>
						</tr>
					</thead>
					<tbody>
						{#each crosswalks as cw}
							<tr>
								<td class="font-medium">{cw.name}</td>
								<td class="text-sm"
									>{cw.source_framework?.str ?? cw.source_framework?.name ?? '—'}</td
								>
								<td class="text-sm"
									>{cw.target_framework?.str ?? cw.target_framework?.name ?? '—'}</td
								>
								<td>
									<span
										class="text-xs px-2 py-0.5 rounded-full {statusBadge[cw.status] ||
											'bg-gray-100 text-gray-700'}"
									>
										{cw.status}
									</span>
								</td>
								<td class="text-sm">{cw.pair_count}</td>
								<td class="text-sm">{cw.reviewed_count}</td>
								<td class="text-xs text-gray-500">{formatDate(cw.generated_at)}</td>
								<td>
									<div class="flex gap-1">
										<a
											href="/experimental/crosswalks/{cw.id}"
											class="btn btn-sm bg-primary-500 text-white hover:bg-primary-600"
										>
											<i class="fa-solid fa-eye mr-1"></i> Open
										</a>
										<button
											type="button"
											class="btn btn-sm variant-ghost-error"
											onclick={() => deleteCrosswalk(cw.id)}
											title="Delete"
											aria-label="Delete"
										>
											<i class="fa-solid fa-trash"></i>
										</button>
									</div>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>

	{#if librarySources.length > 0}
		<section class="card p-4 space-y-3">
			<div class="flex items-start justify-between gap-4 flex-wrap">
				<div>
					<h2 class="text-lg font-semibold">
						<i class="fa-solid fa-copy mr-1"></i> Clone from library
					</h2>
					<p class="text-xs text-gray-500">
						Start a draft from an existing library-imported crosswalk. All its pairs are copied in
						as reviewed; Regenerate will add AI suggestions for any gaps.
					</p>
				</div>
				<div class="flex items-center gap-2">
					<input
						class="input input-sm w-56"
						type="search"
						placeholder="Filter by name, framework, provider…"
						bind:value={librarySearch}
					/>
					<span class="text-xs text-gray-500 whitespace-nowrap">
						{filteredLibrary.length} total
					</span>
				</div>
			</div>
			{#if cloneError}
				<p class="text-sm text-red-600">{cloneError}</p>
			{/if}
			<div class="overflow-x-auto">
				<table class="table table-compact w-full">
					<thead>
						<tr>
							<th>Name</th>
							<th>Source</th>
							<th>Target</th>
							<th>Provider</th>
							<th>Pairs</th>
							<th class="w-32"></th>
						</tr>
					</thead>
					<tbody>
						{#each libraryPageRows as src}
							{@const key = `${src.stored_library_id}:${src.set_urn}`}
							<tr>
								<td class="font-medium">{src.name ?? '—'}</td>
								<td class="text-sm">{src.source_framework?.name ?? '—'}</td>
								<td class="text-sm">{src.target_framework?.name ?? '—'}</td>
								<td class="text-xs text-gray-500">{src.provider ?? '—'}</td>
								<td class="text-sm">{src.pair_count}</td>
								<td>
									<button
										type="button"
										class="btn btn-sm bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-50"
										onclick={() => cloneFromLibrary(src)}
										disabled={cloneBusyId === key}
										title="Clone this mapping into an editable draft"
									>
										{#if cloneBusyId === key}
											<i class="fa-solid fa-spinner fa-spin mr-1"></i>
										{:else}
											<i class="fa-solid fa-copy mr-1"></i>
										{/if}
										Clone
									</button>
								</td>
							</tr>
						{/each}
						{#if libraryPageRows.length === 0}
							<tr>
								<td colspan="6" class="text-center text-sm text-gray-400 py-4"> No matches. </td>
							</tr>
						{/if}
					</tbody>
				</table>
			</div>
			{#if libraryPageCount > 1}
				<div class="flex items-center justify-end gap-2 text-xs pt-1">
					<button
						type="button"
						class="btn btn-sm bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-40"
						onclick={() => (libraryPage = Math.max(1, libraryPage - 1))}
						disabled={libraryPage === 1}
						aria-label="Previous page"
					>
						<i class="fa-solid fa-chevron-left"></i>
					</button>
					<span class="text-gray-600">
						Page <b>{libraryPage}</b> / {libraryPageCount}
					</span>
					<button
						type="button"
						class="btn btn-sm bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-40"
						onclick={() => (libraryPage = Math.min(libraryPageCount, libraryPage + 1))}
						disabled={libraryPage === libraryPageCount}
						aria-label="Next page"
					>
						<i class="fa-solid fa-chevron-right"></i>
					</button>
				</div>
			{/if}
		</section>
	{/if}
</div>
