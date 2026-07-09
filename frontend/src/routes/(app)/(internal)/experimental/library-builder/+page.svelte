<script lang="ts">
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';

	$pageTitle = 'Library Builder';

	let { data } = $props();
	let drafts: any[] = $state(data.drafts ?? []);
	let customLibraries: any[] = $state(data.customLibraries ?? []);

	let statusMessage = $state('');
	let statusType: 'success' | 'error' | '' = $state('');
	let statusTimeout: ReturnType<typeof setTimeout> | null = null;

	function setStatus(message: string, type: 'success' | 'error') {
		statusMessage = message;
		statusType = type;
		if (statusTimeout) clearTimeout(statusTimeout);
		if (type === 'success') {
			statusTimeout = setTimeout(() => {
				statusMessage = '';
				statusType = '';
			}, 3000);
		}
	}

	// --- Create form -------------------------------------------------------
	let showCreate = $state(false);
	let creating = $state(false);
	let newName = $state('');
	let newPackager = $state('');
	let newRefId = $state('');
	let identityCheck: { urn?: string; conflicts?: any[]; error?: string } | null = $state(null);
	let checkTimeout: ReturnType<typeof setTimeout> | null = null;

	const IDENTITY_RE = /^[a-z0-9_-]+$/;

	function scheduleIdentityCheck() {
		identityCheck = null;
		if (checkTimeout) clearTimeout(checkTimeout);
		if (!IDENTITY_RE.test(newPackager) || !IDENTITY_RE.test(newRefId)) return;
		checkTimeout = setTimeout(async () => {
			const params = new URLSearchParams({ packager: newPackager, ref_id: newRefId });
			const res = await fetch(`/experimental/library-builder?${params}`);
			identityCheck = await res.json();
		}, 350);
	}

	async function createDraft() {
		creating = true;
		try {
			const res = await fetch('/experimental/library-builder', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					action: 'create',
					name: newName || newRefId,
					packager: newPackager,
					ref_id: newRefId
				})
			});
			const result = await res.json();
			if (!res.ok) throw new Error(JSON.stringify(result));
			window.location.href = `/experimental/library-builder/${result.id}`;
		} catch (e: any) {
			setStatus(e.message, 'error');
			creating = false;
		}
	}

	// --- Adopt -------------------------------------------------------------
	let adoptSource = $state('');
	let adopting = $state(false);

	async function adoptLibrary() {
		if (!adoptSource) return;
		adopting = true;
		try {
			const res = await fetch('/experimental/library-builder', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ action: 'adopt', stored_library: adoptSource })
			});
			const result = await res.json();
			if (res.status === 409 && result.draft) {
				window.location.href = `/experimental/library-builder/${result.draft}`;
				return;
			}
			if (!res.ok) throw new Error(result.error || JSON.stringify(result));
			window.location.href = `/experimental/library-builder/${result.id}`;
		} catch (e: any) {
			setStatus(e.message, 'error');
			adopting = false;
		}
	}

	// --- Delete ------------------------------------------------------------
	async function deleteDraft(draft: any) {
		if (!confirm(`Delete draft "${draft.name}"? The published library, if any, is not affected.`))
			return;
		const res = await fetch(`/experimental/library-builder?id=${draft.id}`, { method: 'DELETE' });
		if (res.ok) {
			drafts = drafts.filter((d) => d.id !== draft.id);
			setStatus('Draft deleted', 'success');
		} else {
			setStatus('Failed to delete draft', 'error');
		}
	}

	function objectsSummary(draft: any): string {
		const meta = draft.objects_meta ?? {};
		const parts = Object.entries(meta).map(([k, v]) => `${v} ${k.replaceAll('_', ' ')}`);
		return parts.length ? parts.join(', ') : 'empty';
	}
</script>

<div class="space-y-6">
	<!-- Top bar -->
	<div class="card p-4">
		<p class="text-xs text-surface-600-400 mb-4">
			Author a whole library (framework, controls, threats, matrices…) as a draft document, then
			publish it through the standard library loader. Adopt your custom libraries or clone from
			existing ones.
		</p>
		<div class="flex flex-wrap items-center justify-between gap-4">
			<div class="flex items-center gap-2">
				<button
					type="button"
					class="btn btn-sm bg-primary-500 text-white hover:bg-primary-600 transition-colors"
					onclick={() => (showCreate = !showCreate)}
				>
					<i class="fa-solid fa-plus mr-1"></i>
					New Library Draft
				</button>
				{#if customLibraries.length > 0}
					<select class="select w-64 text-sm" bind:value={adoptSource}>
						<option value="">Adopt a custom library…</option>
						{#each customLibraries as library}
							<option value={library.id}>{library.name} (v{library.version})</option>
						{/each}
					</select>
					<button
						type="button"
						class="btn btn-sm variant-ghost-primary"
						onclick={adoptLibrary}
						disabled={!adoptSource || adopting}
					>
						{#if adopting}
							<i class="fa-solid fa-spinner fa-spin mr-1"></i>
						{:else}
							<i class="fa-solid fa-file-import mr-1"></i>
						{/if}
						Adopt
					</button>
				{/if}
			</div>
			{#if statusMessage}
				<span
					class="text-xs px-2 py-1 rounded-full transition-opacity {statusType === 'error'
						? 'bg-red-100 text-red-700'
						: 'bg-green-100 text-green-700'}"
				>
					<i class="fa-solid {statusType === 'error' ? 'fa-circle-xmark' : 'fa-circle-check'} mr-1"
					></i>
					{statusMessage}
				</span>
			{/if}
		</div>

		{#if showCreate}
			<div class="mt-4 border-t border-surface-200-800 pt-4 grid grid-cols-1 md:grid-cols-4 gap-3">
				<label class="label text-sm">
					<span>{m.name()}</span>
					<input class="input" type="text" bind:value={newName} placeholder="My security library" />
				</label>
				<label class="label text-sm">
					<span>Packager</span>
					<input
						class="input"
						type="text"
						bind:value={newPackager}
						oninput={scheduleIdentityCheck}
						placeholder="my-org"
					/>
				</label>
				<label class="label text-sm">
					<span>Reference ID</span>
					<input
						class="input"
						type="text"
						bind:value={newRefId}
						oninput={scheduleIdentityCheck}
						placeholder="my-library"
					/>
				</label>
				<div class="flex items-end">
					<button
						type="button"
						class="btn btn-sm variant-filled-primary"
						onclick={createDraft}
						disabled={creating || !IDENTITY_RE.test(newPackager) || !IDENTITY_RE.test(newRefId)}
					>
						{#if creating}
							<i class="fa-solid fa-spinner fa-spin mr-1"></i>
						{/if}
						Create
					</button>
				</div>
				<div class="md:col-span-4 text-xs space-y-1">
					{#if newPackager && !IDENTITY_RE.test(newPackager)}
						<p class="text-red-600">Packager must match [a-z0-9_-]+</p>
					{/if}
					{#if newRefId && !IDENTITY_RE.test(newRefId)}
						<p class="text-red-600">Reference ID must match [a-z0-9_-]+</p>
					{/if}
					{#if identityCheck?.urn}
						<p class="text-surface-500 font-mono">{identityCheck.urn}</p>
						{#if identityCheck.conflicts?.length}
							<p class="text-amber-600">
								<i class="fa-solid fa-triangle-exclamation mr-1"></i>
								This identity collides with {identityCheck.conflicts.length} existing object(s):
								{identityCheck.conflicts
									.slice(0, 3)
									.map((c: any) => `${c.kind} ${c.urn}`)
									.join('; ')}{identityCheck.conflicts.length > 3 ? '…' : ''}
								— publishing will conflict unless you pick another identity.
							</p>
						{:else}
							<p class="text-green-600">
								<i class="fa-solid fa-circle-check mr-1"></i>Identity is free.
							</p>
						{/if}
					{/if}
				</div>
			</div>
		{/if}
	</div>

	<!-- Drafts -->
	<div class="card p-4">
		<h3 class="text-lg font-semibold mb-3">
			<i class="fa-solid fa-boxes-packing mr-1"></i>
			Library Drafts
		</h3>
		{#if drafts.length > 0}
			<div class="table-container">
				<table class="table table-compact w-full">
					<thead>
						<tr>
							<th>{m.name()}</th>
							<th>URN</th>
							<th>{m.version()}</th>
							<th>Contents</th>
							<th>{m.status()}</th>
							<th class="w-40"></th>
						</tr>
					</thead>
					<tbody>
						{#each drafts as draft}
							<tr>
								<td class="font-medium">{draft.name}</td>
								<td class="text-xs font-mono text-surface-600-400 max-w-64 truncate">
									{draft.urn}
								</td>
								<td class="text-sm">v{draft.version}</td>
								<td class="text-sm text-surface-600-400">{objectsSummary(draft)}</td>
								<td>
									{#if draft.identity_locked}
										<span class="badge variant-filled-success text-xs">
											<i class="fa-solid fa-cloud-arrow-up mr-0.5"></i>Published
										</span>
									{:else}
										<span class="badge variant-ghost-surface text-xs">Draft</span>
									{/if}
								</td>
								<td class="space-x-1">
									<a
										href="/experimental/library-builder/{draft.id}"
										class="btn btn-sm variant-filled-primary"
									>
										<i class="fa-solid fa-pen-to-square mr-1"></i>
										Edit
									</a>
									<button
										type="button"
										class="btn btn-sm variant-ghost-error"
										onclick={() => deleteDraft(draft)}
										aria-label="Delete draft"
									>
										<i class="fa-solid fa-trash"></i>
									</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<p class="text-sm text-surface-500 py-4 text-center">
				No library drafts yet. Create one from scratch or adopt one of your custom libraries.
			</p>
		{/if}
	</div>
</div>
