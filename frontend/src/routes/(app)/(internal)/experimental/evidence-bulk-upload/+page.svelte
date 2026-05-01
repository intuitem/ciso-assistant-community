<script lang="ts">
	import { goto } from '$app/navigation';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { pageTitle } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
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

	$pageTitle = m.bulkEvidenceUpload();

	const toastStore = getToastStore();

	let folderId = $state('');
	let strategy = $state<ConflictStrategy>('skip');
	let entries = $state<FileEntry[]>([]);
	let busy = $state(false);
	let summary = $state<BatchSummary | null>(null);

	function removeEntry(id: string) {
		entries = entries.filter((e) => e.id !== id);
	}

	function clearQueue() {
		entries = [];
		summary = null;
	}

	async function submit() {
		if (!folderId) {
			toastStore.trigger({ message: m.pickTargetDomainFirst() });
			return;
		}
		if (entries.length === 0) {
			toastStore.trigger({ message: m.pickAtLeastOneFile() });
			return;
		}

		busy = true;
		summary = null;

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
		entries = [...entries];

		try {
			const res = await fetch('', { method: 'POST', body: fd });
			const payload = (await res.json()) as BatchResponse | { error?: string };

			if (!res.ok) {
				const msg = (payload as { error?: string }).error || m.uploadFailed();
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

			const byField = new Map<string, BatchResultRow>();
			for (const r of ok.results) byField.set(r.field, r);

			for (const e of entries) {
				const r = byField.get(e.field);
				if (!r) {
					e.status = 'error';
					e.outcome = 'error';
					e.message = m.noResultReturnedForFile();
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
						e.message = m.sameContentAs({ name: r.evidence_name });
					}
				}
			}
			entries = [...entries];

			toastStore.trigger({
				message: m.batchDoneSummary({
					created: summary.created,
					revisions: summary.revision_added,
					replaced: summary.replaced,
					renamed: summary.renamed,
					unchanged: summary.skipped + summary.duplicate,
					errors: summary.errors
				})
			});
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			toastStore.trigger({ message: m.networkErrorWithMessage({ message: msg }) });
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
</script>

<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
	<!-- Form -->
	<section class="lg:col-span-2 bg-white shadow-sm py-5 px-6 space-y-5 card">
		<header>
			<h4 class="h4 font-bold flex items-center gap-2">
				<i class="fa-solid fa-cloud-arrow-up text-indigo-600"></i>
				{m.bulkEvidenceUpload()}
			</h4>
			<p class="text-sm text-gray-600 mt-1">{m.bulkEvidenceUploadDescription()}</p>
		</header>

		<div class="space-y-1.5">
			<label for="folder" class="block text-sm font-medium text-gray-900">
				{m.targetDomain()} <span class="text-red-500">*</span>
			</label>
			<select
				id="folder"
				bind:value={folderId}
				disabled={busy}
				class="w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
			>
				<option value="">{m.selectADomain()}</option>
				{#each data.folders as folder}
					<option value={folder.id}>{folder.str || folder.name}</option>
				{/each}
			</select>
		</div>

		<div class="space-y-1.5">
			<div class="block text-sm font-medium text-gray-900">
				{m.conflictStrategy()} <span class="text-red-500">*</span>
			</div>
			<ConflictStrategyPicker bind:strategy disabled={busy} />
		</div>

		<div class="space-y-1.5">
			<DirectoryFilePicker bind:entries disabled={busy} />
		</div>

		<div class="flex flex-wrap gap-2 pt-2 border-t border-gray-100">
			<button
				type="button"
				class="btn preset-filled"
				onclick={submit}
				disabled={busy || entries.length === 0 || !folderId}
			>
				{#if busy}
					<i class="fa-solid fa-spinner fa-spin mr-2"></i>{m.uploading()}
				{:else}
					<i class="fa-solid fa-upload mr-2"></i>{m.uploadNFiles({ count: entries.length })}
				{/if}
			</button>
			<button
				type="button"
				class="btn preset-outlined"
				onclick={clearQueue}
				disabled={busy || (entries.length === 0 && !summary)}
			>
				<i class="fa-solid fa-broom mr-2"></i>{m.reset()}
			</button>
			<button type="button" class="btn" onclick={() => goto('/experimental')} disabled={busy}>
				{m.cancel()}
			</button>
		</div>
	</section>

	<!-- Results panel -->
	<aside class="lg:col-span-1 bg-white shadow-sm py-5 px-6 space-y-3 card">
		<h5 class="font-semibold text-sm uppercase tracking-wide text-gray-500">{m.results()}</h5>
		{#if summary}
			<BatchUploadResults {summary} />
		{:else}
			<p class="text-sm text-gray-500">{m.summaryWillAppearHere()}</p>
		{/if}
	</aside>

	<!-- Queue (full width) -->
	<section class="lg:col-span-3 bg-white shadow-sm py-5 px-6 space-y-3 card">
		<div class="flex items-center justify-between">
			<h5 class="font-semibold text-sm uppercase tracking-wide text-gray-500">
				{m.queue()}
				{#if entries.length > 0}
					<span class="ml-1 text-gray-400 normal-case tracking-normal">({entries.length})</span>
				{/if}
			</h5>
		</div>
		{#if entries.length === 0}
			<p class="text-sm text-gray-500">{m.noFilesQueuedYet()}</p>
		{:else}
			<BatchUploadQueueTable {entries} onRemove={removeEntry} disabled={busy} />
		{/if}
	</section>
</div>
