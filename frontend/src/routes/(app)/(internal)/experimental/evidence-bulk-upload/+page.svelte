<script lang="ts">
	import { goto } from '$app/navigation';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { pageTitle } from '$lib/utils/stores';
	import DirectoryFilePicker from '$lib/components/BatchUpload/DirectoryFilePicker.svelte';
	import ConflictStrategyPicker from '$lib/components/BatchUpload/ConflictStrategyPicker.svelte';
	import BatchUploadQueueTable from '$lib/components/BatchUpload/BatchUploadQueueTable.svelte';
	import BatchUploadResults from '$lib/components/BatchUpload/BatchUploadResults.svelte';
	import type {
		ConflictStrategy,
		FileEntry,
		BatchResponse,
		BatchSummary,
		BatchResultRow
	} from '$lib/components/BatchUpload/types';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	$pageTitle = 'Bulk evidence upload';

	const toastStore = getToastStore();

	let folderId = $state('');
	let strategy = $state<ConflictStrategy>('skip');
	let entries = $state<FileEntry[]>([]);
	let busy = $state(false);
	let summary = $state<BatchSummary | null>(null);

	function removeEntry(id: string) {
		entries = entries.filter((e) => e.id !== id);
	}

	async function submit() {
		if (!folderId) {
			toastStore.trigger({ message: 'Pick a target folder first.' });
			return;
		}
		if (entries.length === 0) {
			toastStore.trigger({ message: 'Pick at least one file.' });
			return;
		}

		busy = true;
		summary = null;

		// Assign multipart field names + flip every row to "uploading"
		const fd = new FormData();
		fd.append('folder', folderId);
		fd.append('conflict_strategy', strategy);
		const manifest = entries.map((e, i) => {
			const field = `file_${i}`;
			e.field = field;
			e.status = 'uploading';
			e.outcome = undefined;
			e.message = undefined;
			fd.append(field, e.file, e.file.name);
			return { field, name: e.name, rel_path: e.relPath || null };
		});
		fd.append('manifest', JSON.stringify(manifest));
		entries = [...entries]; // trigger reactivity

		try {
			const res = await fetch('', {
				method: 'POST',
				body: fd
			});
			const payload = (await res.json()) as BatchResponse | { error?: string };

			if (!res.ok) {
				const msg = (payload as { error?: string }).error || 'Upload failed';
				toastStore.trigger({ message: msg });
				for (const e of entries) {
					e.status = 'error';
					e.outcome = 'error';
					e.message = msg;
				}
				entries = [...entries];
				return;
			}

			const ok = payload as BatchResponse;
			summary = ok.summary;

			// Map results back to entries by `field`
			const byField = new Map<string, BatchResultRow>();
			for (const r of ok.results) byField.set(r.field, r);

			for (const e of entries) {
				const r = byField.get(e.field);
				if (!r) {
					e.status = 'error';
					e.outcome = 'error';
					e.message = 'No result returned for this file';
					continue;
				}
				e.outcome = r.outcome;
				e.evidenceId = r.evidence_id;
				e.revisionId = r.revision_id;
				e.version = r.version;
				e.renamedTo = r.renamed_to;
				if (r.outcome === 'error') {
					e.status = 'error';
					e.message = typeof r.error === 'string' ? r.error : JSON.stringify(r.error);
				} else {
					e.status = 'done';
					if (r.outcome === 'duplicate' && r.evidence_name) {
						e.message = `Same content as "${r.evidence_name}"`;
					}
				}
			}
			entries = [...entries];

			toastStore.trigger({
				message: `Done — ${summary.created} created, ${summary.revision_added} revisions, ${summary.replaced} replaced, ${summary.renamed} renamed, ${summary.skipped + summary.duplicate} unchanged, ${summary.errors} error(s).`
			});
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			toastStore.trigger({ message: `Network error: ${msg}` });
			for (const e of entries) {
				if (e.status === 'uploading') {
					e.status = 'error';
					e.outcome = 'error';
					e.message = msg;
				}
			}
			entries = [...entries];
		} finally {
			busy = false;
		}
	}

	function reset() {
		entries = [];
		summary = null;
	}
</script>

<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
	<div class="lg:col-span-2 bg-white shadow-sm py-4 px-6 space-y-4 card">
		<div>
			<h4 class="h4 font-bold">
				<i class="fa-solid fa-cloud-arrow-up mr-2"></i>Bulk evidence upload
			</h4>
			<p class="text-sm text-gray-600">
				Upload multiple files (or a whole directory) as evidences in one shot. Duplicate files (same
				SHA-256 inside the target folder) are detected automatically. Name collisions are resolved
				according to the strategy you pick below.
			</p>
		</div>

		<div class="space-y-2">
			<label for="folder" class="block text-sm font-medium text-gray-900">Target folder *</label>
			<select
				id="folder"
				bind:value={folderId}
				disabled={busy}
				class="w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
			>
				<option value="">Select a folder</option>
				{#each data.folders as folder}
					<option value={folder.id}>{folder.str || folder.name}</option>
				{/each}
			</select>
		</div>

		<div class="space-y-2">
			<div class="block text-sm font-medium text-gray-900">Conflict strategy *</div>
			<ConflictStrategyPicker bind:strategy disabled={busy} />
		</div>

		<div class="space-y-2">
			<div class="block text-sm font-medium text-gray-900">Files</div>
			<DirectoryFilePicker bind:entries disabled={busy} />
		</div>

		<div class="flex gap-2 pt-2">
			<button
				type="button"
				class="btn preset-filled"
				onclick={submit}
				disabled={busy || entries.length === 0 || !folderId}
			>
				{#if busy}
					<i class="fa-solid fa-spinner fa-spin mr-2"></i>Uploading…
				{:else}
					<i class="fa-solid fa-upload mr-2"></i>Upload {entries.length} file{entries.length === 1
						? ''
						: 's'}
				{/if}
			</button>
			<button type="button" class="btn preset-outlined" onclick={reset} disabled={busy}>
				Reset
			</button>
			<button type="button" class="btn" onclick={() => goto('/experimental')} disabled={busy}>
				Cancel
			</button>
		</div>
	</div>

	<div class="lg:col-span-1 bg-white shadow-sm py-4 px-6 space-y-4 card">
		<h5 class="font-semibold">Results</h5>
		{#if summary}
			<BatchUploadResults {summary} />
		{:else}
			<p class="text-sm text-gray-500">A summary will appear here once the batch completes.</p>
		{/if}
	</div>

	<div class="lg:col-span-3 bg-white shadow-sm py-4 px-6 space-y-2 card">
		<h5 class="font-semibold">Queue</h5>
		{#if entries.length === 0}
			<p class="text-sm text-gray-500">No files queued yet.</p>
		{:else}
			<BatchUploadQueueTable {entries} onRemove={removeEntry} disabled={busy} />
		{/if}
	</div>
</div>
