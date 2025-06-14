<script lang="ts">
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { driverInstance } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import type { ModalComponent, ModalSettings, ModalStore } from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import type { ActionData, PageData } from './$types';

	import { onMount } from 'svelte';

	export let data: PageData;
	export let form: ActionData;
	$: URLModel = data.URLModel;

	const modalStore: ModalStore = getModalStore();

	function modalCreateForm(): void {
		let modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.createForm,
				model: data.model
			}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: safeTranslate('add-' + data.model.localName)
		};
		modalStore.trigger(modal);
	}

	function modalFolderImportForm(): void {
		let modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.model['folderImportForm'],
				model: data.model['folderImportModel'],
				importFolder: true,
				formAction: '?/importFolder',
				enctype: 'multipart/form-data',
				dataType: 'form'
			}
		};
		let modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: safeTranslate('importFolder')
		};
		modalStore.trigger(modal);
	}

	function handleKeyDown(event: KeyboardEvent) {
		if (event.metaKey || event.ctrlKey) return;
		if (document.activeElement?.tagName !== 'BODY') return;

		// Check if 'c' is pressed and no input fields are currently focused
		if (
			event.key.toLowerCase() === 'c' &&
			document.activeElement?.tagName !== 'INPUT' &&
			document.activeElement?.tagName !== 'TEXTAREA'
		) {
			// Prevent default 'c' key behavior
			event.preventDefault();

			// Check if the add button exists and is not in a disabled list
			if (
				![
					'risk-matrices',
					'frameworks',
					'requirement-mapping-sets',
					'user-groups',
					'role-assignments'
				].includes(URLModel)
			) {
				modalCreateForm();
			}
		}
	}

	function handleClickForGT() {
		setTimeout(() => {
			$driverInstance?.moveNext();
		}, 300);
	}
	onMount(() => {
		// Add event listener when component mounts
		window.addEventListener('keydown', handleKeyDown);

		// Cleanup event listener when component is destroyed
		return () => {
			window.removeEventListener('keydown', handleKeyDown);
		};
	});
</script>

{#if data.table}
	<div class="shadow-lg">
		{#key URLModel}
			<ModelTable source={data.table} deleteForm={data.deleteForm} {URLModel}>
				<div slot="addButton">
					<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-sm">
						{#if !['risk-matrices', 'frameworks', 'requirement-mapping-sets', 'user-groups', 'role-assignments', 'qualifications'].includes(URLModel)}
							<button
								class="inline-block border-e p-3 btn-mini-primary w-12 focus:relative"
								data-testid="add-button"
								id="add-button"
								title={safeTranslate('add-' + data.model.localName)}
								on:click={modalCreateForm}
								on:click={handleClickForGT}
								><i class="fa-solid fa-file-circle-plus"></i>
							</button>
							{#if ['applied-controls', 'assets'].includes(URLModel)}
								<a
									href="{URLModel}/export/"
									class="inline-block p-3 btn-mini-tertiary w-12 focus:relative"
									title={m.exportButton()}
									data-testid="export-button"><i class="fa-solid fa-download mr-2" /></a
								>
							{/if}
							{#if URLModel === 'assets'}
								<a
									href="assets/graph/"
									class="inline-block p-3 btn-mini-secondary w-12 focus:relative"
									title={m.exploreButton()}
									data-testid="viz-button"><i class="fa-solid fa-diagram-project"></i></a
								>
							{/if}
							{#if URLModel === 'folders'}
								<button
									class="text-gray-50 inline-block border-e p-3 bg-sky-400 hover:bg-sky-300 w-12 focus:relative"
									data-testid="import-button"
									title={safeTranslate('importFolder')}
									on:click={modalFolderImportForm}
									><i class="fa-solid fa-file-import"></i>
								</button>
								<a
									href="x-rays/inspect"
									class="inline-block p-3 btn-mini-secondary w-12 focus:relative"
									title={m.exploreButton()}
									data-testid="viz-button"><i class="fa-solid fa-diagram-project"></i></a
								>
							{/if}
						{:else if URLModel === 'risk-matrices'}
							<a
								href="/libraries?object_type=risk_matrices"
								on:click={handleClickForGT}
								class="inline-block p-3 btn-mini-primary w-12 focus:relative"
								data-testid="add-button"
								id="add-button"
								title={m.importMatrices()}><i class="fa-solid fa-file-import mr-2" /></a
							>
						{:else if URLModel === 'frameworks'}
							<a
								href="/libraries?object_type=frameworks"
								on:click={handleClickForGT}
								class="inline-block p-3 btn-mini-primary w-12 focus:relative"
								data-testid="add-button"
								id="add-button"
								title={m.importFrameworks()}><i class="fa-solid fa-file-import mr-2" /></a
							>
						{:else if URLModel === 'requirement-mapping-sets'}
							<a
								href="/libraries?object_type=requirement_mapping_sets"
								class="inline-block p-3 btn-mini-primary w-12 focus:relative"
								data-testid="add-button"
								id="add-button"
								title={m.importMappings()}><i class="fa-solid fa-file-import mr-2" /></a
							>
						{/if}
					</span>
				</div>
			</ModelTable>
		{/key}
	</div>
{/if}
