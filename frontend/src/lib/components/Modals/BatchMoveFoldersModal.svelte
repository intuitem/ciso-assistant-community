<script lang="ts">
	import { m } from '#paraglide/messages.js';
	import { onMount } from 'svelte';
	import { getModalStore, type ModalStore } from './stores';
	import { createPickerForm } from '#lib/components/AssetGraph/picker.js';
	import FolderTreeSelect from '#lib/components/Forms/FolderTreeSelect.svelte';
	import CascadeGroupList, {
		type CascadeGroup
	} from '#lib/components/Modals/CascadeGroupList.svelte';

	/** Response of `folders/move-preview`: the selected domains the caller may move,
	 * and what they carry along. */
	type MovePreview = {
		subjects: { id: string; name: string; below_selected: boolean }[];
		carried: { count: number; hidden_count: number; grouped_objects: CascadeGroup[] };
	};

	interface Props {
		parent: { onClose: () => void };
		ids: string[];
		/** Runs the batch change of `parent_folder` to the picked domain. */
		onConfirm: (value: string) => void;
	}

	let { parent, ids, onConfirm }: Props = $props();

	const modalStore: ModalStore = getModalStore();

	const cBase = 'card bg-surface-100-900 border border-surface-500 p-6 w-modal space-y-6';
	const cHeader = 'text-xl font-medium text-surface-950-50';

	const { form: pickerForm } = createPickerForm('parent_folder');
	const pickerValues = pickerForm.form;

	let preview = $state<MovePreview | null>(null);
	let loading = $state(true);
	let fetchError = $state(false);

	// Selected domains the caller may not change: their rows would fail while the
	// rest moved, so they must be deselected first.
	const notMovableCount = $derived(preview ? ids.length - preview.subjects.length : 0);
	const flattenedNames = $derived(
		(preview?.subjects ?? []).filter((s) => s.below_selected).map((s) => s.name)
	);
	const carriedTotal = $derived(preview ? preview.carried.count + preview.carried.hidden_count : 0);
	const canConfirm = $derived(
		preview !== null &&
			preview.subjects.length > 0 &&
			notMovableCount === 0 &&
			!!$pickerValues.parent_folder
	);

	onMount(async () => {
		try {
			const res = await fetch('/fe-api/folders/move-preview', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ ids })
			});
			if (res.status === 403) {
				// None of the selected domains may be moved by the caller.
				preview = { subjects: [], carried: { count: 0, hidden_count: 0, grouped_objects: [] } };
			} else if (!res.ok) {
				throw new Error(`HTTP ${res.status}`);
			} else {
				preview = await res.json();
			}
		} catch (e) {
			fetchError = true;
			console.error('Failed to fetch the move preview', e);
		} finally {
			loading = false;
		}
	});

	function handleConfirm() {
		if (!canConfirm) return;
		onConfirm(String($pickerValues.parent_folder));
		parent.onClose();
	}
</script>

{#if $modalStore[0]}
	<div
		class="modal-example-form {cBase}"
		role="dialog"
		aria-modal="true"
		aria-labelledby="modal-title"
	>
		<header id="modal-title" class={cHeader} data-testid="modal-title">
			{$modalStore[0].title ?? '(title missing)'}
		</header>

		<article>{m.batchActionConfirmChange({ count: ids.length })}</article>

		<FolderTreeSelect
			form={pickerForm}
			field="parent_folder"
			label={m.parentDomain()}
			excludedIds={ids}
			writePermission="add_folder"
		/>

		{#if loading}
			<div class="text-sm text-surface-600-400">{m.loading()}</div>
		{:else if fetchError}
			<div class="p-4 bg-error-50-950 text-error-900-100 text-sm">{m.errorFetching()}</div>
		{:else if preview}
			{#if notMovableCount > 0}
				<p class="text-sm font-medium text-error-600-400" data-testid="batch-move-not-allowed">
					{m.batchMoveNotAllowed({ count: notMovableCount })}
				</p>
			{/if}
			{#if flattenedNames.length > 0}
				<p class="text-sm font-medium text-amber-600" data-testid="batch-move-flatten-warning">
					{m.batchMoveFlattenWarning({ names: flattenedNames.join(', ') })}
				</p>
			{/if}
			{#if carriedTotal > 0}
				<div class="p-4 bg-blue-50 dark:bg-blue-500/15 border-l-2 border-blue-400">
					<div class="text-sm font-medium text-surface-950-50 mb-3">
						{m.batchMoveCarriedNotice({ count: carriedTotal })}
					</div>
					<div class="max-h-64 overflow-y-auto space-y-1">
						<CascadeGroupList groups={preview.carried.grouped_objects} idPrefix="mov" />
						{#if preview.carried.hidden_count}
							<p
								class="px-3 pt-2 text-xs text-surface-600-400"
								data-testid="cascade-hidden-objects"
							>
								{m.cascadeHiddenObjects({ count: preview.carried.hidden_count })}
							</p>
						{/if}
					</div>
				</div>
			{/if}
		{/if}

		<footer class="flex gap-3 justify-end pt-4 border-t border-surface-200-800">
			<button
				type="button"
				class="px-4 py-2 text-sm font-medium text-surface-700-300 bg-surface-50-950 border border-surface-300-700 hover:bg-surface-50-950"
				data-testid="batch-cancel-button"
				onclick={parent.onClose}
			>
				{m.cancel()}
			</button>
			<button
				class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
				data-testid="batch-confirm-button"
				disabled={!canConfirm}
				onclick={handleConfirm}
			>
				{m.submit()}
			</button>
		</footer>
	</div>
{/if}
