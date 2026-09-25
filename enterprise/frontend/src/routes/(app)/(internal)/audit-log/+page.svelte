<script lang="ts">
	import ModelTable from '$lib/components/ModelTable/ModelTable.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import ExportModal, {
		type ExportGroup,
		type ExportOption
	} from '$lib/components/Modals/ExportModal.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '$lib/components/Modals/stores';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';

	const ACTION_FILTER = {
		component: AutocompleteSelect,
		props: {
			label: 'action',
			options: [
				{ label: 'create', value: '0' },
				{ label: 'update', value: '1' },
				{ label: 'delete', value: '2' },
				{ label: 'access', value: '3' },
				{ label: 'loginFailed', value: '4' }
			],
			multiple: true
		}
	};
	const CONTENT_TYPE_FILTER = {
		component: AutocompleteSelect,
		props: {
			label: 'content_type',
			optionsEndpoint: 'content-types',
			optionsLabelField: 'label',
			optionsValueField: 'value',
			multiple: true
		}
	};

	const modalStore: ModalStore = getModalStore();
	let currentFilterSearch = $state(page.url.search);

	function handleFilterChange(filters: Record<string, any>) {
		const params = new URLSearchParams();
		for (const [field, values] of Object.entries(filters)) {
			if (Array.isArray(values)) {
				for (const v of values) {
					if (v?.value) params.append(v.param ?? field, v.value);
				}
			}
		}
		const search = params.toString();
		currentFilterSearch = search ? `?${search}` : '';
	}

	function buildExportOptions(filterSearch: string): ExportOption[] {
		return [
			{
				titleKey: 'exportTableCsv',
				descriptionKey: 'exportTableCsvDesc',
				format: 'CSV',
				href: `/audit-log/export/${filterSearch}`,
				testId: filterSearch ? 'export-option-csv-filtered' : 'export-option-csv-all'
			},
			{
				titleKey: 'exportTableXlsx',
				descriptionKey: 'exportTableXlsxDesc',
				format: 'XLSX',
				href: `/audit-log/export/xlsx/${filterSearch}`,
				testId: filterSearch ? 'export-option-xlsx-filtered' : 'export-option-xlsx-all'
			}
		];
	}

	function modalExport(): void {
		const groups: ExportGroup[] = currentFilterSearch
			? [
					{ titleKey: 'exportGroupCurrentView', options: buildExportOptions(currentFilterSearch) },
					{ titleKey: 'exportGroupEntireTable', options: buildExportOptions('') }
				]
			: [{ titleKey: '', options: buildExportOptions('') }];
		const modalComponent: ModalComponent = {
			ref: ExportModal,
			props: { title: m.exportOptionsTitle(), groups }
		};
		const modal: ModalSettings = { type: 'component', component: modalComponent };
		modalStore.trigger(modal);
	}
</script>

<main class="bg-surface-50-950 card p-4">
	<ModelTable
		source={{
			head: {
				actor: 'actor',
				action: 'action',
				content_type: 'content_type',
				timestamp: 'timestamp',
				folder: 'folder'
			},
			body: [],
			meta: [],
			filters: {
				action: ACTION_FILTER,
				content_type: CONTENT_TYPE_FILTER
			}
		}}
		URLModel="audit-log"
		baseEndpoint="/audit-log"
		fields={['actor', 'action', 'content_type', 'timestamp', 'folder']}
		thFilter={true}
		thFilterFields={['actor', 'folder']}
		onFilterChange={handleFilterChange}
	>
		{#snippet optButton()}
			<button
				class="inline-block p-3 btn-mini-tertiary w-12 rounded-md border shadow-xs"
				title={m.exportButton()}
				aria-label={m.exportButton()}
				data-testid="export-button"
				onclick={modalExport}
			>
				<i class="fa-solid fa-download"></i>
			</button>
		{/snippet}
	</ModelTable>
</main>
