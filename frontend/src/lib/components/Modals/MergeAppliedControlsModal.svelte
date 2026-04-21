<script lang="ts">
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalStore } from './stores';
	import { getToastStore } from '$lib/components/Toast/stores';
	import { onMount } from 'svelte';
	import type { urlModel } from '$lib/utils/types';
	import type { DataHandler } from '@vincjo/datatables/remote';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';

	interface Props {
		parent: any;
		sourceIds: string[];
		URLModel: urlModel;
		handler: DataHandler;
		onClearSelection: () => void;
	}

	let { parent, sourceIds, URLModel, handler, onClearSelection }: Props = $props();

	const modalStore: ModalStore = getModalStore();
	const toastStore = getToastStore();

	type TargetMode = 'new' | 'selected' | 'another';

	type SourceSummary = { id: string; name: string; folderId: string; folderName: string };

	let sources: SourceSummary[] = $state([]);
	let loadingSources = $state(true);
	// 'selected' is meaningless for a single-source flow (it would self-merge),
	// so default to 'another' (the typical "Replace A with B" entry point).
	let targetMode: TargetMode = $state(sourceIds.length > 1 ? 'selected' : 'another');
	let newTargetName = $state('');
	let newTargetFolderId = $state('');
	let selectedSourceId = $state('');
	let pickedExternalId = $state('');
	let externalControls: { id: string; name: string }[] = $state([]);
	let loadingExternal = $state(false);

	const targetNewSchema = z.object({ name: z.string(), folder: z.string() });
	const _form = superForm(defaults({ name: '', folder: '' }, zod(targetNewSchema)), {
		dataType: 'json',
		taintedMessage: false,
		validators: zod(targetNewSchema),
		SPA: true
	});
	const formStore = _form.form;
	// Mirror form store into local state so the preview $effect triggers on changes.
	formStore.subscribe((v) => {
		newTargetName = v.name ?? '';
		newTargetFolderId = v.folder ?? '';
	});

	let preview: any = $state(null);
	let previewLoading = $state(false);
	let previewError: string | null = $state(null);
	let mdKeepDocId = $state('');
	let submitting = $state(false);

	const cBase = 'card bg-white p-6 w-modal-wide max-w-4xl space-y-5';
	const cHeader = 'text-xl font-medium text-gray-900';

	onMount(async () => {
		try {
			const rows = await Promise.all(
				sourceIds.map((id) =>
					fetch(`/${URLModel}/${id}`)
						.then((r) => (r.ok ? r.json() : null))
						.catch(() => null)
				)
			);
			sources = rows.filter(Boolean).map((r: any) => ({
				id: r.id,
				name: r.name ?? r.str ?? r.id,
				folderId: r.folder?.id ?? '',
				folderName: r.folder?.str ?? r.folder?.name ?? ''
			}));

			if (sources.length > 0) {
				selectedSourceId = sources[0].id;
				_form.form.update((v) => ({
					...v,
					name: sources[0].name,
					folder: sources[0].folderId || ''
				}));
			}
		} finally {
			loadingSources = false;
		}
		await refreshPreview();
	});

	async function loadExternalControls() {
		loadingExternal = true;
		try {
			const res = await fetch(`/${URLModel}/autocomplete`);
			if (res.ok) {
				const data = await res.json();
				const items = (data?.results ?? data) as any[];
				externalControls = items
					.map((it: any) => ({ id: String(it.id), name: it.str ?? it.name ?? it.id }))
					.filter((c) => !sourceIds.includes(c.id));
			}
		} finally {
			loadingExternal = false;
		}
	}

	function buildTargetPayload() {
		if (targetMode === 'new') {
			return {
				type: 'new',
				fields: { name: newTargetName, folder: newTargetFolderId }
			};
		}
		if (targetMode === 'selected') {
			return { type: 'existing', id: selectedSourceId };
		}
		return { type: 'existing', id: pickedExternalId };
	}

	async function refreshPreview() {
		const target = buildTargetPayload();
		// For target=new, the backend needs at least a folder (permission check).
		// The name is cosmetic at dry-run time, so we send a placeholder if empty.
		if (
			(target.type === 'existing' && !target.id) ||
			(target.type === 'new' && !newTargetFolderId)
		) {
			preview = null;
			previewError = null;
			return;
		}
		if (target.type === 'new') {
			target.fields = { ...target.fields, name: target.fields.name || '__preview__' };
		}
		previewLoading = true;
		try {
			const res = await fetch(`/${URLModel}/merge`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					source_ids: sourceIds,
					target,
					dry_run: true
				})
			});
			if (!res.ok) {
				const body = await res.json().catch(() => ({}));
				previewError = body?.body?.detail || body?.detail || JSON.stringify(body);
				// Keep the stale preview visible rather than blanking the section.
			} else {
				preview = await res.json();
				previewError = null;
				if (preview?.managed_document_conflict?.candidates?.length) {
					mdKeepDocId = mdKeepDocId || preview.managed_document_conflict.candidates[0].id;
				}
			}
		} catch (e) {
			previewError = (e as Error).message;
		} finally {
			previewLoading = false;
		}
	}

	// Only refetch the preview when the target *identity* changes — the name is
	// cosmetic and doesn't affect any backend count. Keyed on targetMode +
	// whichever id that mode uses, plus the folder id for target=new (folder is
	// needed to satisfy permission checks server-side).
	$effect(() => {
		void targetMode;
		void selectedSourceId;
		void pickedExternalId;
		void newTargetFolderId;
		refreshPreview();
	});

	$effect(() => {
		if (targetMode === 'another' && externalControls.length === 0 && !loadingExternal) {
			loadExternalControls();
		}
	});

	const mdConflict = $derived(preview?.managed_document_conflict ?? null);
	const canConfirm = $derived(
		!submitting &&
			preview !== null &&
			!previewLoading &&
			(targetMode !== 'new' || (newTargetName.length > 0 && newTargetFolderId.length > 0)) &&
			(targetMode !== 'selected' || selectedSourceId.length > 0) &&
			(targetMode !== 'another' || pickedExternalId.length > 0) &&
			(!mdConflict || mdKeepDocId.length > 0)
	);

	async function handleConfirm() {
		submitting = true;
		try {
			const payload: any = {
				source_ids: sourceIds,
				target: buildTargetPayload()
			};
			if (mdConflict) {
				payload.managed_document_resolution = { keep: mdKeepDocId };
			}
			const res = await fetch(`/${URLModel}/merge`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			if (!res.ok) {
				const body = await res.json().catch(() => ({}));
				const detail = body?.body?.detail || body?.detail || body?.message || m.mergeError();
				toastStore.trigger({
					message: typeof detail === 'string' ? detail : m.mergeError(),
					background: 'preset-filled-error-500'
				});
				return;
			}
			toastStore.trigger({
				message: m.mergeSuccess(),
				background: 'preset-filled-success-500'
			});
			handler.invalidate();
			onClearSelection();
			parent.onClose();
		} finally {
			submitting = false;
		}
	}
</script>

{#if $modalStore[0]}
	<div class={cBase} role="dialog" aria-modal="true" aria-labelledby="merge-modal-title">
		<header id="merge-modal-title" class={cHeader} data-testid="merge-modal-title">
			{m.mergeAppliedControls()}
		</header>

		{#if loadingSources}
			<div class="text-sm text-gray-500">Loading…</div>
		{:else}
			<!-- TARGET PICKER -->
			<section class="space-y-2">
				<h3 class="text-sm font-semibold text-gray-700">{m.selectTargetControl()}</h3>
				<div class="space-y-2">
					{#if sources.length > 1}
						<label class="flex items-start gap-2 cursor-pointer">
							<input type="radio" bind:group={targetMode} value="selected" class="mt-1" />
							<div class="flex-1">
								<div class="text-sm font-medium">{m.useSelectedControlAsTarget()}</div>
								<select
									class="select w-full border border-gray-300 rounded px-3 py-1.5 mt-1 text-sm"
									bind:value={selectedSourceId}
									disabled={targetMode !== 'selected'}
								>
									{#each sources as s}
										<option value={s.id}>{s.name}{s.folderName ? ` — ${s.folderName}` : ''}</option>
									{/each}
								</select>
							</div>
						</label>
					{/if}

					<label class="flex items-start gap-2 cursor-pointer">
						<input type="radio" bind:group={targetMode} value="new" class="mt-1" />
						<div class="flex-1 space-y-2">
							<div class="text-sm font-medium">{m.createNewMergedControl()}</div>
							<input
								type="text"
								class="input w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
								placeholder={m.name()}
								value={$formStore.name}
								oninput={(e) =>
									_form.form.update((v) => ({
										...v,
										name: (e.currentTarget as HTMLInputElement).value
									}))}
								disabled={targetMode !== 'new'}
							/>
							<FolderTreeSelect
								form={_form}
								field="folder"
								label={m.domain()}
								disabled={targetMode !== 'new'}
							/>
						</div>
					</label>

					<label class="flex items-start gap-2 cursor-pointer">
						<input type="radio" bind:group={targetMode} value="another" class="mt-1" />
						<div class="flex-1">
							<div class="text-sm font-medium">{m.useExistingControlAsTarget()}</div>
							{#if targetMode === 'another'}
								{#if loadingExternal}
									<div class="text-sm text-gray-500 mt-1">Loading…</div>
								{:else}
									<select
										class="select w-full border border-gray-300 rounded px-3 py-1.5 mt-1 text-sm"
										bind:value={pickedExternalId}
									>
										<option value="" disabled>--</option>
										{#each externalControls as c}
											<option value={c.id}>{c.name}</option>
										{/each}
									</select>
								{/if}
							{/if}
						</div>
					</label>
				</div>
			</section>

			<!-- PREVIEW -->
			<section class="space-y-2 border-t border-gray-200 pt-4">
				<div class="flex items-center gap-2">
					<h3 class="text-sm font-semibold text-gray-700">{m.previewRewireCounts()}</h3>
					{#if previewLoading}
						<i
							class="fa-solid fa-spinner animate-spin text-slate-400 text-xs"
							aria-label="refreshing"
						></i>
					{/if}
				</div>
				{#if previewError && !preview}
					<div class="text-sm text-red-600">{previewError}</div>
				{:else if preview}
					<div
						class="grid grid-cols-2 gap-4 text-sm transition-opacity {previewLoading
							? 'opacity-60'
							: ''}"
					>
						<div>
							<div class="font-medium text-gray-600 mb-1">{m.previewRewireCounts()}</div>
							<ul class="space-y-0.5">
								{#each Object.entries(preview.rewired_preview ?? {}) as [k, v]}
									{#if Number(v) > 0}
										<li class="text-gray-700">
											<span class="font-mono text-xs">{k}</span>: <strong>{v}</strong>
										</li>
									{/if}
								{/each}
							</ul>
						</div>
						<div>
							<div class="font-medium text-gray-600 mb-1">{m.previewUnionedM2M()}</div>
							<ul class="space-y-0.5">
								{#each Object.entries(preview.unioned_m2m_preview ?? {}) as [k, v]}
									{#if Number(v) > 0}
										<li class="text-gray-700">
											<span class="font-mono text-xs">{k}</span>: +<strong>{v}</strong>
										</li>
									{/if}
								{/each}
							</ul>
						</div>
					</div>
					{#if preview.folder_mismatch}
						<div class="rounded bg-amber-50 border border-amber-200 p-3 text-sm text-amber-900">
							<i class="fa-solid fa-triangle-exclamation"></i>
							{m.folderMismatchWarning()}
						</div>
					{/if}
				{/if}
			</section>

			<!-- MANAGED DOCUMENT CONFLICT -->
			{#if mdConflict}
				<section class="space-y-2 border-t border-gray-200 pt-4">
					<h3 class="text-sm font-semibold text-gray-700">
						<i class="fa-solid fa-file-lines text-amber-600"></i>
						{m.managedDocumentConflict()}
					</h3>
					<p class="text-sm text-gray-600">{m.managedDocumentConflictHelp()}</p>
					<div class="space-y-1">
						{#each mdConflict.candidates as doc}
							<label class="flex items-center gap-2 cursor-pointer text-sm">
								<input type="radio" bind:group={mdKeepDocId} value={doc.id} />
								<span>{doc.name}</span>
							</label>
						{/each}
					</div>
				</section>
			{/if}
		{/if}

		<footer class="flex gap-3 justify-end pt-4 border-t border-gray-200">
			<button
				type="button"
				class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
				onclick={parent.onClose}
				disabled={submitting}
			>
				{m.cancel()}
			</button>
			<button
				type="button"
				class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
				disabled={!canConfirm}
				onclick={handleConfirm}
				data-testid="merge-confirm-button"
			>
				{submitting ? '…' : m.mergeConfirm()}
			</button>
		</footer>
	</div>
{/if}
