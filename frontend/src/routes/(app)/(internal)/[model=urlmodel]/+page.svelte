<script lang="ts">
	import { handlers } from 'svelte/legacy';

	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import { safeTranslate } from '$lib/utils/i18n';
	import { driverInstance } from '$lib/utils/stores';
	import { m } from '$paraglide/messages';
	import type { ActionData, PageData } from './$types';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	import { onMount } from 'svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
	let URLModel = $derived(data.URLModel);

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

{#if data?.table}
	<div class="shadow-lg">
		{#key URLModel}
			<ModelTable
				source={data.table}
				deleteForm={data.deleteForm}
				{URLModel}
				disableEdit={['user-groups'].includes(URLModel)}
				disableDelete={['user-groups'].includes(URLModel)}
			>
				{#snippet addButton()}
					<div>
						<span class="inline-flex overflow-hidden rounded-md border bg-white shadow-xs">
							{#if !['risk-matrices', 'frameworks', 'requirement-mapping-sets', 'user-groups', 'role-assignments', 'qualifications'].includes(URLModel)}
								<button
									class="inline-block p-3 btn-mini-primary w-12 focus:relative"
									data-testid="add-button"
									id="add-button"
									title={safeTranslate('add-' + data.model.localName)}
									onclick={handlers(modalCreateForm, handleClickForGT)}
									><i class="fa-solid fa-file-circle-plus"></i>
								</button>
								{#if ['applied-controls', 'assets', 'incidents', 'security-exceptions', 'risk-scenarios'].includes(URLModel)}
									<a
										href="{URLModel}/export/"
										class="inline-block p-3 btn-mini-tertiary w-12 focus:relative"
										title={m.exportButton()}
										data-testid="export-button"><i class="fa-solid fa-download mr-2"></i></a
									>
								{/if}
								{#if URLModel === 'applied-controls'}
									<a
										href="{URLModel}/flash-mode/"
										class="inline-block p-3 btn-mini-secondary w-12 focus:relative"
										title={m.flashMode()}
										data-testid="flash-mode-button"><i class="fa-solid fa-bolt mr-2"></i></a
									>
								{/if}
								{#if ['threats', 'reference-controls'].includes(URLModel)}
									{@const title =
										URLModel === 'threats' ? m.importThreats() : m.importReferenceControls()}
									<Anchor
										href={`/libraries?object_type=${URLModel.replace(/-/g, '_')}`}
										label={m.libraries()}
										class="inline-block p-3 btn-mini-tertiary w-12 focus:relative"
										data-testid="import-button"
										id="import-button"
										{title}><i class="fa-solid fa-file-import mr-2"></i></Anchor
									>
								{/if}
								{#if URLModel === 'assets'}
									<Anchor
										href="assets/graph/"
										class="inline-block p-3 btn-mini-secondary w-12 focus:relative"
										title={m.exploreButton()}
										label={m.inspect()}
										data-testid="viz-button"><i class="fa-solid fa-diagram-project"></i></Anchor
									>
								{/if}
								{#if URLModel === 'folders'}
									<button
										class="text-gray-50 inline-block border-e p-3 bg-sky-400 hover:bg-sky-300 w-12 focus:relative"
										data-testid="import-button"
										title={safeTranslate('importFolder')}
										onclick={modalFolderImportForm}
										><i class="fa-solid fa-file-import"></i>
									</button>
									<Anchor
										href="x-rays/inspect"
										class="inline-block p-3 btn-mini-secondary w-12 focus:relative"
										title={m.exploreButton()}
										label={m.inspect()}
										data-testid="viz-button"><i class="fa-solid fa-diagram-project"></i></Anchor
									>
								{/if}
								{#if URLModel === 'vulnerabilities'}
									<Anchor
										href="vulnerabilities/treemap/"
										class="inline-block p-3 btn-mini-secondary w-12 focus:relative"
										title={m.visualizeButton()}
										label={m.visualize()}
										data-testid="viz-button"><i class="fa-solid fa-chart-pie"></i></Anchor
									>
								{/if}
							{:else if ['risk-matrices', 'frameworks', 'requirement-mapping-sets'].includes(URLModel)}
								{@const href = `/libraries?object_type=${URLModel.replace(/-/g, '_')}`}
								{@const title =
									URLModel === 'risk-matrices'
										? m.importMatrices()
										: URLModel === 'frameworks'
											? m.importFrameworks()
											: m.importMappings()}
								<Anchor
									{href}
									onclick={handleClickForGT}
									label={m.libraries()}
									class="inline-block p-3 btn-mini-tertiary w-12 focus:relative"
									data-testid="import-button"
									id="add-button"
									{title}><i class="fa-solid fa-file-import mr-2"></i></Anchor
								>
							{/if}
						</span>
					</div>
				{/snippet}
				{#snippet badge(key, row)}
					{#if URLModel === 'risk-assessments'}
						{#if key === 'perimeter' && row.meta.ebios_rm_study}
							<span
								class="badge inline-block bg-amber-100 text-amber-800 text-xs px-2 py-0.5 rounded-md border border-amber-200 rotate-[-6deg] font-semibold uppercase tracking-wide"
								>ebios-rm</span
							>
						{/if}
					{/if}
				{/snippet}
				{#if URLModel === 'risk-assessments'}{/if}
			</ModelTable>
		{/key}
	</div>
{/if}
