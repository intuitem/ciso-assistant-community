<script lang="ts">
	import { defaults, superForm } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import { m } from '$paraglide/messages';
	import { getFlash } from 'sveltekit-flash-message';
	import { page } from '$app/stores';
	import { getModalStore, type ModalComponent } from '$lib/components/Modals/stores';
	import WorkflowPreviewModal from './WorkflowPreviewModal.svelte';

	interface Props {
		// The LOADED library the instantiate action lives on (spec D31) —
		// pages showing stored data must resolve the counterpart id.
		loadedLibraryId: string;
		count: number;
	}

	let { loadedLibraryId, count }: Props = $props();

	const flash = getFlash(page);
	const modalStore = getModalStore();

	function openPreview() {
		const component: ModalComponent = {
			ref: WorkflowPreviewModal,
			props: { loadedLibraryId }
		};
		modalStore.trigger({ type: 'component', component });
	}

	let instantiating = $state(false);
	let instantiateFolder = $state('');
	let instantiateBusy = $state(false);

	// Standalone SPA form backing the hierarchical domain picker
	// (FolderTreeSelect requires a SuperForm); the picked id mirrors into
	// instantiateFolder via onChange. Field is target_folder (not "folder")
	// so the personal-space option never appears.
	const folderSchema = z.object({ target_folder: z.string() });
	const _folderForm = superForm(defaults({ target_folder: '' }, zod(folderSchema)), {
		dataType: 'json',
		taintedMessage: false,
		validators: zod(folderSchema),
		SPA: true
	});

	async function instantiateWorkflows() {
		if (!instantiateFolder) return;
		instantiateBusy = true;
		try {
			const res = await fetch(`/loaded-libraries/${loadedLibraryId}/instantiate-workflows`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ folder: instantiateFolder })
			});
			const body = await res.json().catch(() => ({}));
			if (!res.ok) {
				flash.set({ type: 'error', message: String(body.error ?? res.statusText) });
				return;
			}
			const names = (body.workflows ?? []).map((w: any) => w.name).join(', ');
			flash.set({ type: 'success', message: m.workflowInstantiated({ names }) });
			instantiating = false;
		} finally {
			instantiateBusy = false;
		}
	}
</script>

{#if count > 0}
	<div class="space-y-2">
		<div class="flex items-center gap-3">
			<span class="font-medium">
				<i class="fa-solid fa-diagram-project mr-2"></i>{count}
				{m.workflows()}
			</span>
			<button
				type="button"
				class="btn preset-tonal text-sm"
				onclick={openPreview}
				data-testid="preview-workflows"
			>
				<i class="fa-solid fa-eye mr-1"></i>{m.previewWorkflow()}
			</button>
			<button
				type="button"
				class="btn preset-filled-primary-500 text-sm"
				onclick={() => (instantiating = !instantiating)}
				data-testid="instantiate-workflows"
			>
				<i class="fa-solid fa-wand-magic-sparkles mr-1"></i>{m.instantiateWorkflow()}
			</button>
		</div>
		{#if instantiating}
			<div class="flex items-end gap-2">
				<div class="w-64" data-testid="instantiate-folder">
					<FolderTreeSelect
						form={_folderForm}
						field="target_folder"
						label={m.domain()}
						writePermission="add_workflow"
						onChange={(value: any) => (instantiateFolder = value ?? '')}
					/>
				</div>
				<button
					type="button"
					class="btn preset-tonal text-sm"
					disabled={!instantiateFolder || instantiateBusy}
					onclick={instantiateWorkflows}
					data-testid="instantiate-confirm"
				>
					{#if instantiateBusy}
						<i class="fa-solid fa-circle-notch fa-spin mr-1"></i>
					{/if}
					{m.instantiateHere()}
				</button>
			</div>
		{/if}
	</div>
{/if}
