<script lang="ts">
	import { handlers } from 'svelte/legacy';
	import { page } from '$app/state';

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
	import { getToastStore } from '$lib/components/Toast/stores';
	import { invalidateAll } from '$app/navigation';

	interface Props {
		data: PageData;
		form: ActionData;
	}

	let { data, form }: Props = $props();
	const toastStore = getToastStore();
	let URLModel = $derived(data.URLModel);
	let exportPopupOpen = $state(false);
	let pullCatalogOpen = $state(false);
	let currentFilterSearch = $state(page.url.search);

	function handleFilterChange(filters: Record<string, any>) {
		const params = new URLSearchParams();
		for (const [field, values] of Object.entries(filters)) {
			if (Array.isArray(values)) {
				for (const v of values) {
					if (v?.value) params.append(field, v.value);
				}
			}
		}
		const search = params.toString();
		currentFilterSearch = search ? `?${search}` : '';
	}

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
				disableEdit={['user-groups', 'validation-flows'].includes(URLModel)}
				disableDelete={['user-groups'].includes(URLModel)}
				onFilterChange={handleFilterChange}
			>
				{#snippet addButton()}
					<div class="relative">
						<div class="inline-flex overflow-hidden rounded-md border bg-white shadow-xs">
							{#if !['risk-matrices', 'frameworks', 'requirement-mapping-sets', 'user-groups', 'role-assignments', 'qualifications'].includes(URLModel)}
								<button
									class="inline-block p-3 btn-mini-primary w-12 focus:relative"
									data-testid="add-button"
									id="add-button"
									title={safeTranslate('add-' + data.model.localName)}
									aria-label={safeTranslate('add-' + data.model.localName)}
									onclick={handlers(modalCreateForm, handleClickForGT)}
									><i class="fa-solid fa-file-circle-plus"></i>
								</button>
								{#if ['applied-controls', 'assets', 'incidents', 'security-exceptions', 'risk-scenarios', 'processings', 'task-templates', 'entities', 'solutions', 'contracts'].includes(URLModel)}
									<button
										class="inline-block p-3 btn-mini-tertiary w-12 focus:relative"
										title={m.exportButton()}
										data-testid="export-button"
										onclick={() => (exportPopupOpen = !exportPopupOpen)}
									>
										<i class="fa-solid fa-download"></i>
									</button>
								{/if}
								{#if URLModel === 'vulnerabilities'}
									<button
										class="inline-block p-3 btn-mini-tertiary w-12 focus:relative"
										title={m.refreshDueDates()}
										aria-label={m.refreshDueDates()}
										data-testid="refresh-due-dates-button"
										onclick={() => {
											modalStore.trigger({
												type: 'confirm',
												title: m.refreshDueDates(),
												body: m.refreshDueDatesConfirm(),
												response: async (confirmed) => {
													if (!confirmed) return;
													try {
														const res = await fetch('/vulnerabilities/refresh-due-dates', {
															method: 'POST'
														});
														const result = await res.json();
														toastStore.trigger({
															message: result.detail || result.error,
															preset: res.ok ? 'success' : 'error'
														});
														if (res.ok) invalidateAll();
													} catch {
														toastStore.trigger({
															message: m.refreshDueDatesFailed(),
															preset: 'error'
														});
													}
												}
											});
										}}><i class="fa-solid fa-clock-rotate-left"></i></button
									>
								{/if}
								{#if URLModel === 'applied-controls'}
									<a
										href="{URLModel}/flash-mode/{currentFilterSearch}"
										class="inline-block p-3 btn-mini-secondary w-12 focus:relative"
										title={m.flashMode()}
										aria-label={m.flashMode()}
										data-testid="flash-mode-button"><i class="fa-solid fa-bolt mr-2"></i></a
									>
									<a
										href="{URLModel}/kanban-mode/{currentFilterSearch}"
										class="inline-block p-3 btn-mini-quaternary w-12 focus:relative"
										title={m.kanbanMode()}
										aria-label={m.kanbanMode()}
										data-testid="kanban-mode-button"><i class="fa-solid fa-table-columns"></i></a
									>
								{/if}
								{#if URLModel === 'security-advisories'}
									<button
										class="inline-block p-3 w-12 focus:relative bg-blue-50 hover:bg-blue-100"
										title={m.syncKev()}
										aria-label={m.syncKev()}
										data-testid="sync-kev-button"
										onclick={() => {
											modalStore.trigger({
												type: 'confirm',
												title: m.pullCatalog(),
												body: m.syncKev(),
												response: async (confirmed) => {
													if (!confirmed) return;
													try {
														const res = await fetch('/security-advisories/sync-kev', {
															method: 'POST'
														});
														const result = await res.json();
														toastStore.trigger({
															message: result.detail || result.error,
															preset: res.ok ? 'success' : 'error'
														});
														if (res.ok) invalidateAll();
													} catch {
														toastStore.trigger({
															message: m.syncKevFailed(),
															preset: 'error'
														});
													}
												}
											});
										}}>🇺🇸</button
									>
									<button
										class="inline-block p-3 w-12 focus:relative bg-yellow-50 hover:bg-yellow-100"
										title={m.syncEuvd()}
										aria-label={m.syncEuvd()}
										data-testid="sync-euvd-button"
										onclick={() => {
											modalStore.trigger({
												type: 'confirm',
												title: m.pullCatalog(),
												body: m.syncEuvd(),
												response: async (confirmed) => {
													if (!confirmed) return;
													try {
														const res = await fetch('/security-advisories/sync-euvd', {
															method: 'POST'
														});
														const result = await res.json();
														toastStore.trigger({
															message: result.detail || result.error,
															preset: res.ok ? 'success' : 'error'
														});
														if (res.ok) invalidateAll();
													} catch {
														toastStore.trigger({
															message: m.syncEuvdFailed(),
															preset: 'error'
														});
													}
												}
											});
										}}>🇪🇺</button
									>
								{/if}
								{#if URLModel === 'cwes'}
									<button
										class="inline-block p-3 btn-mini-tertiary w-12 focus:relative"
										title={m.syncCweCatalog()}
										aria-label={m.syncCweCatalog()}
										data-testid="sync-cwe-button"
										onclick={async () => {
											try {
												const res = await fetch('/cwes/sync-catalog', { method: 'POST' });
												const result = await res.json();
												toastStore.trigger({
													message: result.detail || result.error,
													preset: res.ok ? 'success' : 'error'
												});
												if (res.ok) invalidateAll();
											} catch {
												toastStore.trigger({
													message: m.syncCweCatalogFailed(),
													preset: 'error'
												});
											}
										}}><i class="fa-solid fa-satellite-dish"></i></button
									>
								{/if}
								{#if ['threats', 'reference-controls', 'metric-definitions'].includes(URLModel)}
									{@const title =
										URLModel === 'threats'
											? m.importThreats()
											: URLModel === 'reference-controls'
												? m.importReferenceControls()
												: m.importMetricDefinitions()}
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
								{#if URLModel === 'entities'}
									<Anchor
										href="entities/graph/"
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
										aria-label={safeTranslate('importFolder')}
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
								{#if URLModel === 'requirement-mapping-sets'}
									<Anchor
										href="requirement-mapping-sets/graph/"
										class="inline-block p-3 btn-mini-secondary w-12 focus:relative"
										title={m.exploreButton()}
										label={m.inspect()}
										data-testid="viz-button"><i class="fa-solid fa-diagram-project"></i></Anchor
									>
								{/if}
							{/if}
						</div>
						{#if exportPopupOpen}
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<div
								class="fixed inset-0 z-40"
								onclick={() => (exportPopupOpen = false)}
								onkeydown={() => {}}
							></div>
							<div
								class="absolute right-0 z-50 mt-1 card whitespace-nowrap bg-white py-2 w-fit shadow-lg"
							>
								<div class="flex flex-col">
									<a
										href="{URLModel}/export/"
										class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200"
										onclick={() => (exportPopupOpen = false)}>... {m.asCSV()}</a
									>
									<a
										href="{URLModel}/export/xlsx/"
										class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200"
										onclick={() => (exportPopupOpen = false)}>... {m.asXLSX()}</a
									>
									{#if URLModel === 'entities'}
										<a
											href="/entities/export/ecosystem/"
											class="block px-4 py-2 text-sm text-gray-800 hover:bg-gray-200"
											onclick={() => (exportPopupOpen = false)}>... {m.exportEcosystem()}</a
										>
									{/if}
								</div>
							</div>
						{/if}
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
