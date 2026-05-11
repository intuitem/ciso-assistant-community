<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import { pageTitle } from '$lib/utils/stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { onDestroy } from 'svelte';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import * as m from '$paraglide/messages';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
		form: any;
	}

	let { data, form }: Props = $props();

	$pageTitle = 'Questionnaire Autopilot';

	// chat_mode is only present in featureflags when ENABLE_CHAT=true at the
	// backend AND an admin has turned it on in global settings. Either gate
	// being off collapses to chat_mode being false-y, so one check covers both.
	const chatEnabled = $derived(Boolean(page.data?.featureflags?.chat_mode));

	const toast = getToastStore();

	// SuperForm wrapper around a single `folder` field so we can drive the
	// standard FolderTreeSelect picker. Mirror its value into a hidden input
	// so the multipart form action picks it up alongside the file.
	const folderSchema = z.object({ folder: z.string().nullable().optional() });
	const folderPickerForm = superForm(defaults({ folder: null }, zod(folderSchema)), {
		dataType: 'json',
		taintedMessage: false,
		SPA: true,
		validators: zod(folderSchema)
	});
	let selectedFolderId = $state('');
	const _folderUnsub = folderPickerForm.form.subscribe((v: any) => {
		selectedFolderId = v?.folder ?? '';
	});
	onDestroy(_folderUnsub);

	let title = $state('');
	let submitting = $state(false);

	$effect(() => {
		if (form?.error) {
			toast.trigger({ message: form.error });
		}
	});

	let deletingId = $state<string | null>(null);

	// File picker / drop zone state
	let fileInputEl: HTMLInputElement | null = $state(null);
	let selectedFile = $state<File | null>(null);
	let isDraggingOver = $state(false);

	function onFileChange(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		selectedFile = input.files?.[0] ?? null;
	}

	function clearSelectedFile(event: MouseEvent) {
		event.preventDefault();
		event.stopPropagation();
		selectedFile = null;
		if (fileInputEl) fileInputEl.value = '';
	}

	function onDropZoneDragOver(event: DragEvent) {
		event.preventDefault();
		isDraggingOver = true;
	}

	function onDropZoneDragLeave() {
		isDraggingOver = false;
	}

	function onDropZoneDrop(event: DragEvent) {
		event.preventDefault();
		isDraggingOver = false;
		const file = event.dataTransfer?.files?.[0];
		if (!file || !fileInputEl) return;
		// Push the dropped file into the native input so the form action
		// picks it up as if the user had clicked browse.
		const dt = new DataTransfer();
		dt.items.add(file);
		fileInputEl.files = dt.files;
		selectedFile = file;
	}

	function formatBytes(n: number): string {
		if (n < 1024) return `${n} B`;
		if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
		return `${(n / (1024 * 1024)).toFixed(1)} MB`;
	}

	async function deleteRun(run: { id: string; title: string; filename: string }) {
		const label = run.title || run.filename || 'this run';
		if (
			!confirm(
				`Delete "${label}"? This removes the questionnaire, its extracted questions, and any agent runs / proposals attached to it.`
			)
		) {
			return;
		}
		deletingId = run.id;
		try {
			const res = await fetch(`/experimental/questionnaire-autopilot/${run.id}`, {
				method: 'DELETE'
			});
			if (res.status === 204 || res.ok) {
				toast.trigger({ message: `Deleted "${label}".` });
				await invalidateAll();
			} else {
				const data = await res.json().catch(() => ({}));
				toast.trigger({ message: data.detail || 'Failed to delete the run.' });
			}
		} finally {
			deletingId = null;
		}
	}

	const statusBadge = (status: string) => {
		switch (status) {
			case 'pending':
			case 'parsing':
				return 'bg-yellow-100 text-yellow-800';
			case 'parsed':
				return 'bg-green-100 text-green-800';
			case 'failed':
				return 'bg-red-100 text-red-800';
			default:
				return 'bg-gray-100 text-gray-800';
		}
	};
</script>

{#if !chatEnabled}
	<div class="bg-white shadow-sm py-6 px-6 card max-w-2xl border-l-4 border-amber-400">
		<h4 class="h4 font-bold">
			<i class="fa-solid fa-robot mr-2 text-amber-600"></i>AI chat is required
		</h4>
		<p class="text-sm text-gray-700 mt-2">
			Questionnaire Autopilot uses the same LLM and retrieval pipeline as AI Chat. It's currently
			disabled on this deployment.
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
					<i class="fa-solid fa-file-import mr-2"></i>Questionnaire Autopilot
				</h4>
				<p class="text-sm text-gray-600 mt-1">
					Upload a customer security questionnaire (.xlsx) and scope it to a domain. Once parsed,
					you'll review the detected sheet/columns before any prefill happens.
				</p>
				<p class="text-xs text-gray-500 mt-1">
					Experimental — no LLM prefill yet, just upload + parse + column mapping.
				</p>
			</div>

			<form
				method="post"
				action="?/upload"
				enctype="multipart/form-data"
				use:enhance={() => {
					submitting = true;
					return async ({ update }) => {
						await update();
						submitting = false;
					};
				}}
				class="space-y-4"
			>
				<div class="rounded-lg p-4 border-2 border-green-500">
					<FolderTreeSelect
						form={folderPickerForm}
						field="folder"
						label={m.folder() + ' *'}
						contentTypes={['DO']}
					/>
					<input type="hidden" name="folder" value={selectedFolderId} />
					<p class="text-xs text-gray-500 mt-1">
						The agent will look up applied controls, evidences, and existing assessments inside this
						domain when answering questions.
					</p>
				</div>

				<div class="rounded-lg p-4 border-2 border-blue-500">
					<label for="title" class="block text-sm font-medium text-gray-900">
						Title (optional)
					</label>
					<input
						id="title"
						name="title"
						type="text"
						bind:value={title}
						maxlength="200"
						placeholder="e.g. Acme Corp — Vendor Security Review Q2"
						class="mt-1.5 w-full rounded-lg border-gray-300 text-gray-700 sm:text-sm"
					/>
				</div>

				<div>
					<label for="file" class="block text-sm font-medium text-gray-900 mb-1.5">
						Questionnaire file (.xlsx) *
					</label>
					<label
						for="file"
						ondragover={onDropZoneDragOver}
						ondragleave={onDropZoneDragLeave}
						ondrop={onDropZoneDrop}
						class="flex flex-col items-center justify-center gap-2 px-4 py-8 rounded-lg
						border-2 border-dashed cursor-pointer transition-colors
						{isDraggingOver
							? 'border-pink-500 bg-pink-50'
							: selectedFile
								? 'border-green-500 bg-green-50'
								: 'border-gray-300 bg-gray-50 hover:border-pink-400 hover:bg-pink-50/40'}"
					>
						{#if selectedFile}
							<i class="fa-solid fa-file-excel text-3xl text-green-600"></i>
							<div class="text-center">
								<div class="text-sm font-medium text-gray-900 truncate max-w-[420px]">
									{selectedFile.name}
								</div>
								<div class="text-xs text-gray-500 mt-0.5">
									{formatBytes(selectedFile.size)} · click to change or
									<button
										type="button"
										onclick={clearSelectedFile}
										class="text-red-600 hover:text-red-700 underline"
									>
										remove
									</button>
								</div>
							</div>
						{:else}
							<i
								class="fa-solid {isDraggingOver ? 'fa-arrow-down' : 'fa-cloud-arrow-up'} text-3xl
								{isDraggingOver ? 'text-pink-600' : 'text-gray-400'}"
							></i>
							<div class="text-center">
								<div class="text-sm font-medium text-gray-700">
									{isDraggingOver ? 'Drop the file here' : 'Click to choose a file or drop it here'}
								</div>
								<div class="text-xs text-gray-500 mt-0.5">.xlsx only</div>
							</div>
						{/if}
						<input
							id="file"
							name="file"
							type="file"
							accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
							class="sr-only"
							required
							bind:this={fileInputEl}
							onchange={onFileChange}
						/>
					</label>
				</div>

				<div class="flex gap-2">
					<button type="submit" class="btn preset-filled" disabled={submitting}>
						<i class="fa-solid fa-upload mr-2"></i>
						{submitting ? 'Uploading…' : 'Upload & parse'}
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
		</div>

		<div class="col-span-1 p-4">
			<h5 class="font-semibold mb-2 text-sm">Recent runs</h5>
			{#if data.runs.length === 0}
				<p class="text-sm text-gray-500">No runs yet. Upload a questionnaire to start.</p>
			{:else}
				<div class="space-y-2">
					{#each data.runs as run}
						<div
							class="group relative p-3 bg-white rounded shadow-sm hover:shadow-md transition-shadow"
						>
							<a href="/experimental/questionnaire-autopilot/{run.id}" class="block pr-7">
								<div class="flex justify-between items-start gap-2">
									<div class="text-sm font-medium truncate font-mono">
										{run.title || run.filename}
									</div>
									<span class="text-xs px-2 py-0.5 rounded {statusBadge(run.status)}">
										{run.status}
									</span>
								</div>
								{#if run.title && run.filename && run.title !== run.filename}
									<div class="text-xs text-gray-500 mt-0.5 truncate" title={run.filename}>
										{run.filename}
									</div>
								{/if}
								<div class="text-xs text-gray-500 mt-1 truncate">
									{run.folder?.str || run.folder?.name || '—'}
								</div>
								<div class="text-xs text-gray-400">
									{new Date(run.created_at).toLocaleString()}
								</div>
							</a>
							<button
								type="button"
								class="absolute top-2 right-2 text-gray-300 hover:text-red-600 transition-colors disabled:opacity-50"
								title="Delete this run"
								aria-label="Delete this run"
								disabled={deletingId === run.id}
								onclick={() => deleteRun(run)}
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
