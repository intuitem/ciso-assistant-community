<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import { pageTitle } from '$lib/utils/stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import DirectoryFilePicker from '$lib/components/BatchUpload/DirectoryFilePicker.svelte';
	import ConflictStrategyPicker from '$lib/components/BatchUpload/ConflictStrategyPicker.svelte';
	import BatchUploadQueueTable from '$lib/components/BatchUpload/BatchUploadQueueTable.svelte';
	import type {
		ConflictStrategy,
		FileEntry,
		BatchResponse,
		BatchResultRow
	} from '$lib/components/BatchUpload/types';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	$pageTitle = 'Audit Prefill';

	// Same gate as questionnaire autopilot: needs ENABLE_CHAT + chat_mode flag.
	const chatEnabled = $derived(Boolean(page.data?.featureflags?.chat_mode));

	const toast = getToastStore();

	// null = pre-pick (cards shown). Once chosen, the form unfolds.
	let mode = $state<'existing' | 'upload' | null>(null);

	// Form state — common across modes.
	let folderId = $state('');
	let complianceAssessmentId = $state('');
	let strictness = $state<'fast' | 'thorough'>('fast');
	let submitting = $state(false);

	// Upload-mode only.
	let strategy = $state<ConflictStrategy>('skip');
	let entries = $state<FileEntry[]>([]);

	let deletingId = $state<string | null>(null);

	const candidateAudits = $derived(
		folderId ? data.complianceAssessments.filter((ca: any) => ca.folder?.id === folderId) : []
	);

	// Reset audit when folder changes — the previous pick is no longer in the
	// filtered list.
	$effect(() => {
		void folderId;
		complianceAssessmentId = '';
	});

	async function deleteRun(run: any, event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();
		const label =
			run.config?.wave === 2
				? `Wave 2 run from ${new Date(run.created_at).toLocaleString()}`
				: `Wave 1 run from ${new Date(run.created_at).toLocaleString()}`;
		if (
			!confirm(
				`Delete "${label}"? Removes the agent's audit trail; created applied controls and approved RA verdicts stay.`
			)
		) {
			return;
		}
		deletingId = run.id;
		try {
			const res = await fetch(`/experimental/audit-prefill/${run.id}`, {
				method: 'DELETE'
			});
			if (res.status === 204 || res.ok) {
				toast.trigger({ message: 'Run deleted.' });
				await invalidateAll();
			} else {
				const data = await res.json().catch(() => ({}));
				toast.trigger({ message: data.detail || 'Failed to delete the run.' });
			}
		} finally {
			deletingId = null;
		}
	}

	function statusBadge(s: string) {
		switch (s) {
			case 'queued':
			case 'running':
				return 'bg-yellow-100 text-yellow-800';
			case 'succeeded':
				return 'bg-green-100 text-green-800';
			case 'failed':
			case 'cancelled':
				return 'bg-red-100 text-red-800';
			default:
				return 'bg-gray-100 text-gray-800';
		}
	}

	async function runUpload(): Promise<boolean> {
		// Returns true if we should continue to start-prefill, false to halt.
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

		let res: Response;
		try {
			res = await fetch('/experimental/audit-prefill/upload', {
				method: 'POST',
				body: fd
			});
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			toast.trigger({ message: `Network error: ${msg}` });
			for (const e of entries) {
				if (e.status === 'uploading') {
					e.status = 'error';
					e.outcome = 'error';
					e.message = msg;
				}
			}
			entries = [...entries];
			return false;
		}

		const payload = (await res.json().catch(() => ({}))) as
			| BatchResponse
			| { error?: string; detail?: string };

		if (!res.ok) {
			const msg =
				(payload as { detail?: string; error?: string }).detail ||
				(payload as { error?: string }).error ||
				'Upload failed.';
			toast.trigger({ message: msg });
			for (const e of entries) {
				e.status = 'error';
				e.outcome = 'error';
				e.message = msg;
			}
			entries = [...entries];
			return false;
		}

		const ok = payload as BatchResponse;
		const summary = ok.summary;

		// Map per-file results back onto the queue so the table shows
		// "added revision" / "duplicate" / "error" badges.
		const byField = new Map<string, BatchResultRow>();
		for (const r of ok.results) byField.set(r.field, r);
		for (const e of entries) {
			const r = byField.get(e.field);
			if (!r) {
				e.status = 'error';
				e.outcome = 'error';
				e.message = 'No result returned for file.';
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
			}
		}
		entries = [...entries];

		const ingested = summary.created + summary.revision_added + summary.replaced + summary.renamed;
		// Warn-and-continue: even if some files failed, prefill still has
		// value (folder may have older evidences). Toast surfaces the loss.
		if (summary.errors > 0) {
			toast.trigger({
				message: `Uploaded ${ingested}/${summary.total} (${summary.errors} errors). Starting prefill anyway.`
			});
		} else if (summary.total > 0) {
			toast.trigger({
				message: `Uploaded ${ingested} file${ingested === 1 ? '' : 's'}. Starting prefill…`
			});
		}
		return true;
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		if (submitting) return;
		if (!folderId) {
			toast.trigger({ message: 'Pick a folder first.' });
			return;
		}
		if (!complianceAssessmentId) {
			toast.trigger({ message: 'Pick an audit to prefill.' });
			return;
		}
		if (mode === 'upload' && entries.length === 0) {
			toast.trigger({ message: 'Add files to the queue or switch back to "Use existing folder".' });
			return;
		}

		submitting = true;
		try {
			if (mode === 'upload' && entries.length > 0) {
				const proceed = await runUpload();
				if (!proceed) {
					submitting = false;
					return;
				}
			}

			const res = await fetch('/experimental/audit-prefill/start', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					folder: folderId,
					compliance_assessment: complianceAssessmentId,
					strictness
				})
			});
			const payload = await res.json().catch(() => ({}));
			if (!res.ok) {
				toast.trigger({ message: payload.detail || 'Failed to start audit prefill.' });
				submitting = false;
				return;
			}
			await goto(`/experimental/audit-prefill/${payload.id}`);
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			toast.trigger({ message: `Network error: ${msg}` });
			submitting = false;
		}
	}

	function pickMode(m: 'existing' | 'upload') {
		mode = m;
		// Reset upload-only state when switching to existing.
		if (m === 'existing') {
			entries = [];
		}
	}
</script>

{#if !chatEnabled}
	<div class="bg-white shadow-sm py-6 px-6 card max-w-2xl border-l-4 border-amber-400">
		<h4 class="h4 font-bold">
			<i class="fa-solid fa-robot mr-2 text-amber-600"></i>AI chat is required
		</h4>
		<p class="text-sm text-gray-700 mt-2">
			Audit Prefill uses the same LLM and retrieval pipeline as AI Chat. It's currently disabled on
			this deployment.
		</p>
		<p class="text-xs text-gray-500 mt-2">
			Ask an administrator to enable <code class="font-mono">ENABLE_CHAT</code> on the backend and
			turn on the <em>chat mode</em> feature flag in Settings.
		</p>
	</div>
{:else}
	<div class="grid grid-cols-3 gap-4">
		<div class="col-span-2 bg-white shadow-sm py-4 px-6 space-y-4 card">
			<div>
				<h4 class="h4 font-bold">
					<i class="fa-solid fa-wand-magic-sparkles mr-2"></i>Audit Prefill
				</h4>
				<p class="text-sm text-gray-600 mt-1">
					Point the agent at a folder full of evidences and pick an audit. Wave 1 extracts the
					controls described in your docs (deduped against existing perimeter controls). Wave 2
					proposes a result + linked controls for each requirement assessment in the audit.
				</p>
			</div>

			{#if !mode}
				<!-- Mode chooser cards -->
				<div class="grid grid-cols-2 gap-4 pt-2">
					<button
						type="button"
						class="flex flex-col items-center text-center gap-2 p-6 rounded-lg border-2 border-gray-200 hover:border-pink-500 hover:bg-pink-50/40 transition-colors"
						onclick={() => pickMode('existing')}
					>
						<i class="fa-solid fa-folder-open text-4xl text-pink-600"></i>
						<div class="text-base font-semibold">Use existing folder</div>
						<div class="text-xs text-gray-500">
							You've already loaded the relevant evidences. Just pick the folder and the audit.
						</div>
					</button>
					<button
						type="button"
						class="flex flex-col items-center text-center gap-2 p-6 rounded-lg border-2 border-gray-200 hover:border-pink-500 hover:bg-pink-50/40 transition-colors"
						onclick={() => pickMode('upload')}
					>
						<i class="fa-solid fa-cloud-arrow-up text-4xl text-pink-600"></i>
						<div class="text-base font-semibold">Upload new content</div>
						<div class="text-xs text-gray-500">
							You have a directory of files (PDFs, .docx, .md, …) to upload first. We'll add them to
							the folder you pick, then start the prefill.
						</div>
					</button>
				</div>
			{:else}
				<!-- Back to chooser -->
				<button
					type="button"
					class="text-xs text-pink-600 hover:underline"
					onclick={() => (mode = null)}
					disabled={submitting}
				>
					<i class="fa-solid fa-chevron-left mr-1"></i>
					Change mode
					<span class="text-gray-500">
						(currently: {mode === 'upload' ? 'Upload new content' : 'Use existing folder'})
					</span>
				</button>

				<form onsubmit={handleSubmit} class="space-y-4">
					<!-- Folder picker — required in both modes -->
					<div class="space-y-1.5">
						<label for="folder" class="block text-sm font-medium text-gray-900">
							Folder <span class="text-red-500">*</span>
						</label>
						<select
							id="folder"
							name="folder"
							bind:value={folderId}
							disabled={submitting}
							class="w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
						>
							<option value="">Pick a folder…</option>
							{#each data.folders as folder}
								<option value={folder.id}>{folder.str || folder.name}</option>
							{/each}
						</select>
						<p class="text-xs text-gray-500">
							{#if mode === 'upload'}
								Destination for the new files. The agent then scans every Evidence in this folder.
							{:else}
								The agent scans every Evidence already in this folder. AppliedControls in this
								folder are used as the dedup target.
							{/if}
						</p>
					</div>

					{#if mode === 'upload'}
						<!-- Upload-only block -->
						<div class="space-y-3 p-4 rounded-lg border-2 border-pink-200 bg-pink-50/30">
							<div class="text-xs font-semibold uppercase tracking-wide text-pink-700">
								Upload step
							</div>
							<div class="space-y-1.5">
								<div class="block text-sm font-medium text-gray-900">
									Conflict strategy <span class="text-red-500">*</span>
								</div>
								<ConflictStrategyPicker bind:strategy disabled={submitting} />
							</div>
							<div class="space-y-1.5">
								<DirectoryFilePicker bind:entries disabled={submitting} />
							</div>
							{#if entries.length > 0}
								<BatchUploadQueueTable
									{entries}
									onRemove={(id) => (entries = entries.filter((e) => e.id !== id))}
									disabled={submitting}
								/>
							{/if}
						</div>
					{/if}

					<!-- Audit picker -->
					<div class="space-y-1.5">
						<label for="ca" class="block text-sm font-medium text-gray-900">
							Audit <span class="text-red-500">*</span>
						</label>
						<select
							id="ca"
							name="compliance_assessment"
							bind:value={complianceAssessmentId}
							disabled={submitting || !folderId}
							class="w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
						>
							<option value="">
								{folderId ? 'Pick an audit in this folder…' : 'Pick a folder first'}
							</option>
							{#each candidateAudits as ca}
								<option value={ca.id}>
									{ca.str || ca.name} ({ca.framework?.str || ca.framework?.name || '—'})
								</option>
							{/each}
						</select>
						{#if folderId && candidateAudits.length === 0}
							<p class="text-xs text-amber-600">
								No audits in this folder. Create a ComplianceAssessment in it first.
							</p>
						{/if}
					</div>

					<!-- Strictness -->
					<div class="space-y-1.5">
						<div class="block text-sm font-medium text-gray-900">
							Strictness <span class="text-red-500">*</span>
						</div>
						<div class="flex gap-3">
							<label
								class="flex items-start gap-2 p-3 rounded border-2 cursor-pointer flex-1
								{strictness === 'fast' ? 'border-pink-500 bg-pink-50' : 'border-gray-200 hover:border-gray-300'}"
							>
								<input
									type="radio"
									name="strictness"
									value="fast"
									bind:group={strictness}
									class="mt-0.5"
								/>
								<span class="text-sm">
									<span class="font-semibold block">Fast</span>
									<span class="text-xs text-gray-500">
										Cheaper. Skips observation drafting on Wave 2.
									</span>
								</span>
							</label>
							<label
								class="flex items-start gap-2 p-3 rounded border-2 cursor-pointer flex-1
								{strictness === 'thorough'
									? 'border-pink-500 bg-pink-50'
									: 'border-gray-200 hover:border-gray-300'}"
							>
								<input
									type="radio"
									name="strictness"
									value="thorough"
									bind:group={strictness}
									class="mt-0.5"
								/>
								<span class="text-sm">
									<span class="font-semibold block">Thorough</span>
									<span class="text-xs text-gray-500">
										Drafts observation text per requirement. Slower, more tokens.
									</span>
								</span>
							</label>
						</div>
					</div>

					<div class="flex gap-2">
						<button
							type="submit"
							class="btn preset-filled"
							disabled={submitting ||
								!folderId ||
								!complianceAssessmentId ||
								(mode === 'upload' && entries.length === 0)}
						>
							<i class="fa-solid fa-play mr-2"></i>
							{#if submitting}
								{mode === 'upload' && entries.some((e) => e.status === 'uploading')
									? 'Uploading…'
									: 'Starting…'}
							{:else if mode === 'upload'}
								Upload &amp; Start Wave 1
							{:else}
								Start Wave 1
							{/if}
						</button>
						<button
							type="button"
							class="btn"
							onclick={() => goto('/experimental')}
							disabled={submitting}
						>
							Cancel
						</button>
					</div>
				</form>
			{/if}
		</div>

		<div class="col-span-1 p-4">
			<h5 class="font-semibold mb-2 text-sm">Recent prefill runs</h5>
			{#if data.runs.length === 0}
				<p class="text-sm text-gray-500">No runs yet. Start one to begin.</p>
			{:else}
				<div class="space-y-2">
					{#each data.runs as run}
						<div
							class="group relative p-3 bg-white rounded shadow-sm hover:shadow-md transition-shadow"
						>
							<a href="/experimental/audit-prefill/{run.id}" class="block pr-7">
								<div class="flex justify-between items-start gap-2">
									<div class="text-sm font-medium truncate font-mono">
										Wave {run.config?.wave ?? '?'} · {run.strictness}
									</div>
									<span class="text-xs px-2 py-0.5 rounded {statusBadge(run.status)}">
										{run.status}
									</span>
								</div>
								<div class="text-xs text-gray-500 mt-0.5 truncate">
									{run.folder?.str || run.folder?.name || '—'}
								</div>
								<div class="text-xs text-gray-400">
									{new Date(run.created_at).toLocaleString()}
								</div>
							</a>
							<button
								type="button"
								class="absolute top-2 right-2 text-gray-300 hover:text-red-600 transition-colors disabled:opacity-50"
								title={run.status === 'running'
									? 'Cancel the run first, then delete.'
									: 'Delete this run'}
								aria-label="Delete this run"
								disabled={deletingId === run.id || run.status === 'running'}
								onclick={(e) => deleteRun(run, e)}
							>
								{#if deletingId === run.id}
									<i class="fa-solid fa-spinner fa-spin"></i>
								{:else}
									<i class="fa-solid fa-trash text-xs"></i>
								{/if}
							</button>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/if}
