<script lang="ts">
	import { Popover } from '@skeletonlabs/skeleton-svelte';
	import { run } from 'svelte/legacy';

	import { goto as _goto } from '$app/navigation';
	import { page } from '$app/state';
	import TableRowActions from '$lib/components/TableRowActions/TableRowActions.svelte';
	import { ISO_8601_REGEX } from '$lib/utils/constants';
	import { CUSTOM_ACTIONS_COMPONENT, getFieldComponentMap, URL_MODEL_MAP } from '$lib/utils/crud';
	import { safeTranslate, unsafeTranslate } from '$lib/utils/i18n';
	import { toCamelCase } from '$lib/utils/locales.js';
	import { onMount } from 'svelte';

	import { tableA11y } from '$lib/components/ModelTable/actions';
	// Types
	import { browser } from '$app/environment';
	import LecChartPreview from '$lib/components/ModelTable/field/LecChartPreview.svelte';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import type { ListViewFilterConfig, BatchActionConfig } from '$lib/utils/table';
	import { goto, breadcrumbs } from '$lib/utils/breadcrumbs';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { isDark } from '$lib/utils/helpers';
	import { contextMenuActions, listViewFields, getBatchActions } from '$lib/utils/table';
	import BatchActionBar from './BatchActionBar.svelte';
	import type { urlModel } from '$lib/utils/types.js';
	import { countMasked, isMaskedPlaceholder } from '$lib/utils/related-visibility';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	import type { SvelteEvent } from '@skeletonlabs/skeleton-svelte';
	import { DataHandler, type State } from '@vincjo/datatables/remote';
	import { defaults, superForm, type SuperValidated } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';
	import { z, type AnyZodObject } from 'zod';
	import { loadTableData } from './handler';
	import Pagination from './Pagination.svelte';
	import RowCount from './RowCount.svelte';
	import RowsPerPage from './RowsPerPage.svelte';
	import Search from './Search.svelte';
	import Th from './Th.svelte';
	import ThFilter from './ThFilter.svelte';
	import { canPerformAction } from '$lib/utils/access-control';
	import { ContextMenu } from 'bits-ui';
	import { tableHandlers, tableStates } from '$lib/utils/stores';
	import DeleteConfirmModal from '$lib/components/Modals/DeleteConfirmModal.svelte';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';
	import {
		getModalStore,
		type ModalStore,
		type ModalComponent,
		type ModalSettings
	} from '$lib/components/Modals/stores';

	interface Props {
		// Props
		source?: TableSource;
		interactive?: boolean;
		search?: boolean;
		thFilter?: boolean;
		thFilterFields?: string[];
		rowsPerPage?: boolean;
		rowCount?: boolean;
		pagination?: boolean;
		numberRowsPerPage?: number;
		orderBy?: { identifier: string; direction: 'asc' | 'desc' };
		// Props (styles)
		element?: string;
		text?: string;
		backgroundColor?: string;
		color?: string;
		regionHead?: string;
		regionHeadCell?: string;
		regionBody?: string;
		regionCell?: string;
		regionFoot?: string;
		regionFootCell?: string;
		displayActions?: boolean;
		disableCreate?: boolean;
		disableEdit?: boolean;
		disableDelete?: boolean;
		disableView?: boolean;
		identifierField?: string;
		deleteForm?: SuperValidated<AnyZodObject>;
		URLModel?: urlModel;
		baseEndpoint?: string;
		detailQueryParameter?: string;
		fields?: string[];
		canSelectObject?: boolean;
		overrideFilters?: { [key: string]: any[] };
		defaultFilters?: { [key: string]: any[] };
		hideFilters?: boolean;
		tableFilters?: Record<string, ListViewFilterConfig>;
		folderId?: string;
		forcePreventDelete?: boolean;
		forcePreventEdit?: boolean;
		expectedCount?: number;
		onFilterChange?: (filters: Record<string, any>) => void;
		quickFilters?: import('svelte').Snippet<[{ [key: string]: any }, typeof _form, () => void]>;
		optButton?: import('svelte').Snippet;
		selectButton?: import('svelte').Snippet;
		addButton?: import('svelte').Snippet;
		badge?: import('svelte').Snippet<[string, { [key: string]: any }]>;
		actions?: import('svelte').Snippet<[any]>;
		actionsBody?: import('svelte').Snippet;
		actionsHead?: import('svelte').Snippet;
		tail?: import('svelte').Snippet;
	}

	let {
		source = { head: [], body: [] },
		interactive = true,
		search = true,
		thFilter = false,
		thFilterFields = [],
		rowsPerPage = true,
		rowCount = true,
		pagination = true,
		numberRowsPerPage = $tableStates[page.url.pathname]?.rowsPerPage ?? 10,
		orderBy = undefined,
		element = 'table',
		text = 'text-xs',
		backgroundColor = 'bg-white',
		color = '',
		regionHead = '',
		regionHeadCell = 'uppercase bg-white text-gray-700',
		regionBody = 'bg-white',
		regionCell = 'max-w-[65ch] max-h-[8em] overflow-hidden hover:overflow-y-auto',
		regionFoot = '',
		regionFootCell = '',
		displayActions = true,
		disableCreate = false,
		disableEdit = false,
		disableDelete = false,
		disableView = false,
		identifierField = 'id',
		deleteForm = undefined,
		URLModel = undefined,
		baseEndpoint = `/${URLModel}`,
		detailQueryParameter = $bindable(),
		fields = [],
		canSelectObject = false,
		overrideFilters = {},
		defaultFilters = {},
		hideFilters = $bindable(false),
		tableFilters = URLModel &&
		listViewFields[URLModel] &&
		Object.hasOwn(listViewFields[URLModel], 'filters')
			? listViewFields[URLModel].filters
			: {},
		folderId = '',
		forcePreventDelete = false,
		forcePreventEdit = false,
		expectedCount = undefined,
		onFilterChange = () => {},
		quickFilters,
		optButton,
		selectButton,
		addButton,
		badge,
		actions,
		actionsBody,
		actionsHead,
		tail
	}: Props = $props();

	const modalStore: ModalStore = getModalStore();

	let model = $derived(URL_MODEL_MAP[URLModel]);
	const tableSource: TableSource = $derived(
		Object.keys(source.head)
			.filter(
				(key) =>
					!(
						model?.flaggedFields &&
						Object.hasOwn(model.flaggedFields, key) &&
						Object.hasOwn(page.data?.featureflags, model.flaggedFields[key]) &&
						page.data?.featureflags[model.flaggedFields[key]] === false
					)
			)
			.reduce(
				(acc, key) => {
					acc.head[key] = source.head[key];
					return acc;
				},
				{ head: {}, body: source.body, meta: source.meta }
			)
	);

	function onRowClick(
		event: SvelteEvent<MouseEvent | KeyboardEvent, HTMLTableRowElement>,
		rowIndex: number
	): void {
		if (!interactive) return;
		event.preventDefault();
		event.stopPropagation();
		const rowMetaData = $rows[rowIndex].meta;
		if (!rowMetaData[identifierField] || !URLModel) return;

		const preferredLabel =
			URLModel === 'reference-controls' ? rowMetaData.name || rowMetaData.ref_id : undefined;
		const label =
			preferredLabel ||
			rowMetaData.str ||
			rowMetaData.name ||
			rowMetaData.email ||
			rowMetaData.label ||
			rowMetaData[identifierField];

		goto(`/${URLModel}/${rowMetaData[identifierField]}${detailQueryParameter}`, {
			label,
			breadcrumbAction: 'push'
		});
	}

	function onRowKeydown(
		event: SvelteEvent<KeyboardEvent, HTMLTableRowElement>,
		rowIndex: number
	): void {
		if (['Enter', 'Space'].includes(event.code)) onRowClick(event, rowIndex);
	}

	detailQueryParameter = detailQueryParameter ? `?${detailQueryParameter}` : '';

	const user = page.data.user;

	const isRelatedField = (fieldName: string): boolean => relatedFieldNames.has(fieldName);

	let classProp = ''; // Replacing $$props.class

	let classesBase = $derived(`${classProp || backgroundColor}`);
	let classesTable = $derived(`${element} ${text} ${color}`);

	const handler = new DataHandler(
		tableSource.body.map((item: Record<string, any>, index: number) => {
			return {
				...item,
				meta: tableSource.meta
					? tableSource.meta.results
						? { ...tableSource.meta.results[index] }
						: { ...tableSource.meta[index] }
					: undefined
			};
		}),
		{
			rowsPerPage: pagination
				? ($tableStates[page.url.pathname]?.rowsPerPage ?? numberRowsPerPage)
				: 0,
			totalRows: source?.meta?.count
		}
	);
	const rows = handler.getRows();

	const relatedFieldNames = $derived(
		new Set(model?.foreignKeyFields?.map((field) => field.field) ?? [])
	);

	const hiddenRowCount = $derived(typeof expectedCount === 'number' ? expectedCount : 0);

	$tableHandlers[baseEndpoint] = handler;

	handler.onChange((state: State) =>
		loadTableData({
			state,
			URLModel,
			endpoint: baseEndpoint,
			fields:
				fields.length > 0
					? { head: fields, body: fields }
					: {
							head:
								typeof tableSource.head[0] === 'string'
									? Object.values(tableSource.head)
									: Object.keys(tableSource.head),
							body:
								typeof tableSource.body[0] === 'string'
									? Object.values(tableSource.body)
									: Object.keys(tableSource.body)
						},
			featureFlags: page.data?.featureflags
		})
	);

	onMount(() => {
		if (orderBy) {
			orderBy.direction === 'asc'
				? handler.sortAsc(orderBy.identifier)
				: handler.sortDesc(orderBy.identifier);
		}
	});

	const actionsURLModel = URLModel;
	const preventDelete = (row: TableSource) =>
		(actionsURLModel === 'stored-libraries' && (row?.meta?.builtin || row?.meta?.is_loaded)) ||
		(!URLModel?.includes('libraries') && Object.hasOwn(row?.meta, 'urn') && row?.meta?.urn) ||
		row?.meta?.builtin ||
		(URLModel?.includes('campaigns') && row?.meta?.compliance_assessments?.length > 0) ||
		(Object.hasOwn(row?.meta, 'reference_count') && row?.meta?.reference_count > 0) ||
		['severity_changed', 'status_changed'].includes(row?.meta?.entry_type) ||
		forcePreventDelete;
	const preventEdit = (row: TableSource) => forcePreventEdit;

	const tableURLModel = URLModel;

	let contextMenuOpenRow: TableSource | undefined = $state(undefined);

	const filters = source?.filters ?? tableFilters;
	const filteredFields = Object.keys(filters);
	const filterValues: { [key: string]: any } = $state(
		Object.fromEntries(
			filteredFields.map((field: string) => {
				const urlValues = page.url.searchParams.getAll(field).map((value) => ({ value }));
				const defaultValue = defaultFilters[field] || [];
				return [field, urlValues.length > 0 ? urlValues : defaultValue];
			})
		)
	);
	$effect(() => onFilterChange(filterValues));

	run(() => {
		hideFilters = hideFilters || !Object.entries(filters).some(([_, filter]) => !filter.hide);
	});

	$effect(() => {
		for (const field of filteredFields) {
			const filterValue = filterValues[field];
			const overrideFilterValue = overrideFilters[field];
			const finalFilterValue = overrideFilterValue || filterValue;

			const fieldFilterParams = finalFilterValue
				? finalFilterValue.map((v: Record<string, any>) => v.value)
				: [];
			handler.filter(fieldFilterParams, field);
			page.url.searchParams.delete(field);
			if (finalFilterValue) {
				finalFilterValue.forEach(({ value }) => page.url.searchParams.append(field, value));
			}

			const hrefPattern = new RegExp(`^/${URLModel}(\\?.*)?$`);
			const fullPath = page.url.pathname + page.url.search;
			if (hrefPattern.test(fullPath)) {
				breadcrumbs.updateCrumb(hrefPattern, { href: fullPath });
			}
		}
		history.replaceState(history.state, '', page.url.pathname + page.url.search);
		setTimeout(() => {
			handler.invalidate();
		}, 10);
	});

	const filterInitialData: Record<string, string[]> = {};
	// convert URL search params and default filters to filter initial data
	for (const [key, value] of page.url.searchParams) {
		filterInitialData[key] ??= [];
		filterInitialData[key].push(value);
	}
	// Add default filter values if no URL params exist for that field
	for (const field of filteredFields) {
		if (!filterInitialData[field] && filterValues[field]?.length > 0) {
			filterInitialData[field] = filterValues[field].map((v: Record<string, any>) => v.value);
		}
	}
	const zodFiltersObject = {};
	Object.keys(filters).forEach((k) => {
		zodFiltersObject[k] = z.array(z.string()).optional().nullable();
	});
	const _form = superForm(defaults(filterInitialData, zod(z.object(zodFiltersObject))), {
		SPA: true,
		validators: zod(z.object(zodFiltersObject)),
		dataType: 'json',
		invalidateAll: false,
		applyAction: false,
		resetForm: false,
		taintedMessage: false,
		validationMethod: 'auto'
	});

	$effect(() => {
		if (page.form?.form?.posted && page.form?.form?.valid) {
			console.debug('Form posted, invalidating table');
			handler.invalidate();
		}
	});

	let fieldComponentMap = $derived(getFieldComponentMap(URLModel));
	let canCreateObject = $derived(
		model
			? page.params.id
				? canPerformAction({
						user,
						action: 'add',
						model: model.name,
						domain:
							folderId ||
							page.data?.data?.folder?.id ||
							page.data?.data?.folder ||
							page.params.id ||
							user.root_folder_id
					})
				: Object.hasOwn(user.permissions, `add_${model.name}`)
			: false
	);
	let contextMenuCanEditObject = $derived(
		(model
			? page.params.id
				? canPerformAction({
						user,
						action: 'change',
						model: model.name,
						domain:
							model.name === 'folder'
								? contextMenuOpenRow?.meta.id
								: (contextMenuOpenRow?.meta.folder?.id ??
									contextMenuOpenRow?.meta.folder ??
									user.root_folder_id)
					})
				: Object.hasOwn(user.permissions, `change_${model.name}`)
			: false) &&
			(!(contextMenuOpenRow?.meta.builtin || contextMenuOpenRow?.meta.urn) ||
				URLModel === 'terminologies' ||
				URLModel === 'entities')
	);

	let contextMenuDisplayEdit = $derived(
		contextMenuCanEditObject &&
			URLModel &&
			!['frameworks', 'risk-matrices', 'ebios-rm'].includes(URLModel)
	);

	let contextMenuCanDeleteObject = $derived(
		!preventDelete(contextMenuOpenRow ?? { head: [], body: [], meta: [] }) &&
			(model
				? page.params.id
					? canPerformAction({
							user,
							action: 'delete',
							model: model.name,
							domain:
								model.name === 'folder'
									? contextMenuOpenRow?.meta.id
									: (contextMenuOpenRow?.meta.folder?.id ??
										contextMenuOpenRow?.meta.folder ??
										user.root_folder_id)
						})
					: Object.hasOwn(user.permissions, `delete_${model.name}`)
				: false)
	);

	let contextMenuDisplayDelete = $derived(contextMenuCanDeleteObject && deleteForm !== undefined);

	function contextMenuModalConfirmDelete(
		id: string,
		row: { [key: string]: string | number | boolean | null }
	): void {
		const modalComponent: ModalComponent = {
			ref: DeleteConfirmModal,
			props: {
				_form: deleteForm,
				id: id,
				debug: false,
				URLModel: URLModel
			}
		};
		const name =
			URLModel === 'users' && row.first_name
				? `${row.first_name} ${row.last_name} (${row.email})`
				: (row.name ?? row.meta?.str ?? Object.values(row)[0]);
		const body =
			URLModel === 'users'
				? m.deleteUserMessage({ name: name as string })
				: m.deleteModalMessage({ name: name as string });
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.deleteModalTitle(),
			body: body
		};
		modalStore.trigger(modal);
	}

	function contextMenuPromptModalConfirmDelete(
		id: string,
		row: { [key: string]: string | number | boolean | null }
	): void {
		const modalComponent: ModalComponent = {
			ref: PromptConfirmModal,
			props: {
				_form: deleteForm,
				id: id,
				debug: false,
				URLModel: URLModel,
				formAction: '?/delete'
			}
		};
		const name =
			URLModel === 'users' && row.first_name
				? `${row.first_name} ${row.last_name} (${row.email})`
				: (row.name ?? Object.values(row)[0]);
		const body =
			URLModel === 'users'
				? m.deleteUserMessage({ name: name as string })
				: m.deleteModalMessage({ name: name as string });
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: m.deleteModalTitle(),
			body: body
		};
		modalStore.trigger(modal);
	}

	let filterCount = $derived(
		filteredFields?.reduce((acc, field) => acc + filterValues?.[field]?.length, 0)
	);

	let classesHexBackgroundText = $derived((backgroundHexColor: string) => {
		return isDark(backgroundHexColor) ? 'text-white' : '';
	});

	const tail_render = $derived(tail);

	// Multi-value columns that should not be sortable
	const MULTI_VALUE_COLUMNS = [
		'owner',
		'filtering_labels',
		'linked_models',
		'threats',
		'assets',
		'applied_controls',
		'existing_applied_controls',
		'evidences',
		'qualifications',
		'user_groups'
	];

	// Function to check if a column is multi-value and should not be sortable
	const isMultiValueColumn = (key: string): boolean => {
		if (URLModel === 'applied-controls' && key === 'assets') {
			// sort measures by assets
			return false;
		}
		return (
			MULTI_VALUE_COLUMNS.includes(key) ||
			(tableSource.body.length > 0 && Array.isArray(tableSource.body[0][key]))
		);
	};

	// Helper function to convert linked_models snake_case to camelCase for translation
	const convertLinkedModelName = (snakeCaseName: string): string => {
		const mapping: Record<string, string> = {
			compliance_assessments: 'complianceAssessments',
			risk_assessments: 'riskAssessments',
			business_impact_analysis: 'businessImpactAnalysis',
			crq_studies: 'quantitativeRiskStudies',
			ebios_studies: 'ebiosRMStudies',
			entity_assessments: 'entityAssessments',
			findings_assessments: 'findingsAssessments',
			evidences: 'evidences',
			security_exceptions: 'securityExceptions',
			policies: 'policies'
		};
		return mapping[snakeCaseName] || snakeCaseName;
	};

	let openState = $state(false);

	// Batch selection state
	let selectedIds: Set<string> = $state(new Set());

	const currentBatchActions: BatchActionConfig[] = $derived(
		URLModel && model
			? getBatchActions(URLModel).filter((a) =>
					a.type === 'delete'
						? Object.hasOwn(user.permissions, `delete_${model.name}`)
						: Object.hasOwn(user.permissions, `change_${model.name}`)
				)
			: []
	);
	const hasBatchActions = $derived(currentBatchActions.length > 0 && deleteForm !== undefined);

	let selectAllChecked = $derived.by(() => {
		const pageIds = $rows.filter((r: any) => r.meta?.id).map((r: any) => r.meta.id);
		return pageIds.length > 0 && pageIds.every((id: string) => selectedIds.has(id));
	});

	function toggleRowSelection(id: string) {
		const next = new Set(selectedIds);
		if (next.has(id)) {
			next.delete(id);
		} else {
			next.add(id);
		}
		selectedIds = next;
	}

	function toggleSelectAll() {
		const pageIds = $rows.filter((r: any) => r.meta?.id).map((r: any) => r.meta.id);
		if (selectAllChecked) {
			selectedIds = new Set();
		} else {
			selectedIds = new Set(pageIds);
		}
	}

	function clearSelection() {
		selectedIds = new Set();
	}

	// Clear selection when rows change (page/filter change)
	let previousRowSignature = '';
	$effect(() => {
		const sig = $rows.map((r: any) => r.meta?.id).join(',');
		if (previousRowSignature && sig !== previousRowSignature) {
			selectedIds = new Set();
		}
		previousRowSignature = sig;
	});
</script>

<div class="card table-wrap {classesBase}">
	<header class="flex justify-between items-center space-x-8 p-2">
		{#if hasBatchActions && selectedIds.size > 0}
			<BatchActionBar
				{selectedIds}
				actions={currentBatchActions}
				{URLModel}
				{handler}
				onClearSelection={clearSelection}
			/>
		{:else}
			{#if !hideFilters}
				<Popover
					open={openState}
					onOpenChange={(e) => (openState = e.open)}
					positioning={{ placement: 'bottom-start' }}
					autoFocus={false}
					onPointerDownOutside={() => (openState = false)}
					closeOnInteractOutside={false}
				>
					<Popover.Trigger class="btn preset-filled-primary-500 self-end relative">
						<i class="fa-solid fa-filter mr-2"></i>
						{m.filters()}
						{#if filterCount}
							<span class="text-sm">{filterCount}</span>
						{/if}
					</Popover.Trigger>
					<Popover.Positioner class="z-50!">
						<Popover.Content
							class="card p-2 bg-white max-w-lg shadow-lg space-y-2 border border-surface-200"
						>
							<SuperForm {_form} validators={zod(z.object({}))}>
								{#snippet children({ form })}
									{#each filteredFields as field}
										{#if filters[field]?.component}
											{@const FilterComponent = filters[field].component}
											<FilterComponent
												{form}
												{field}
												{...filters[field].props}
												fieldContext="filter"
												label={safeTranslate(filters[field].props?.label)}
												onChange={(value) => {
													const arrayValue = Array.isArray(value) ? value : [value];
													const sanitizedArrayValue = arrayValue.filter(
														(v) => v !== null && v !== undefined
													);

													filterValues[field] = sanitizedArrayValue.map((v) => ({ value: v }));
												}}
											/>
										{/if}
									{/each}
								{/snippet}
							</SuperForm>
						</Popover.Content>
					</Popover.Positioner>
				</Popover>
			{/if}
			{#if search}
				<Search {handler} />
			{/if}
			{#if pagination && rowsPerPage}
				<RowsPerPage {handler} />
			{/if}
			<div class="flex space-x-2 items-center">
				{@render optButton?.()}
				{#if canSelectObject}
					{@render selectButton?.()}
				{/if}
				{#if canCreateObject && !disableCreate}
					{@render addButton?.()}
				{/if}
			</div>
		{/if}
	</header>
	{@render quickFilters?.(filterValues, _form, () => {})}
	{#if hiddenRowCount > 0}
		<div
			class="mx-2 mb-2 rounded border border-yellow-200 bg-yellow-50 px-3 py-2 text-xs text-yellow-800"
		>
			{m.objectsNotVisible({ count: hiddenRowCount })}
		</div>
	{/if}
	<!-- Table -->
	<table
		class="table caption-bottom {classesTable}"
		class:table-interactive={interactive}
		role="grid"
		use:tableA11y
	>
		<thead class="table-head {regionHead}">
			<tr>
				{#if hasBatchActions}
					<th
						class="{regionHeadCell} group/check w-10 text-center cursor-pointer"
						title={m.selectAll()}
						onclick={(e) => {
							e.stopPropagation();
							toggleSelectAll();
						}}
					>
						<span
							class="inline-flex items-center justify-center w-9 h-9 rounded-full transition-colors group-hover/check:bg-black/10 dark:group-hover/check:bg-white/10"
						>
							<input
								type="checkbox"
								class="checkbox pointer-events-none"
								checked={selectAllChecked}
								tabindex={-1}
							/>
						</span>
					</th>
				{/if}
				{#each Object.entries(tableSource.head) as [key, heading]}
					{#if fields.length === 0 || fields.includes(key)}
						<Th {handler} orderBy={isMultiValueColumn(key) ? undefined : key} class={regionHeadCell}
							>{safeTranslate(heading)}</Th
						>
					{/if}
				{/each}
				{#if displayActions}
					<th class="{regionHeadCell} select-none text-end"></th>
				{/if}
			</tr>
			{#if thFilter}
				<tr>
					{#if hasBatchActions}
						<th></th>
					{/if}
					{#each Object.entries(tableSource.head) as [key, _]}
						{#if thFilterFields.includes(key)}
							<ThFilter {handler} filterBy={key} />
						{:else}
							<th></th>
						{/if}
					{/each}
				</tr>
			{/if}
		</thead>
		<ContextMenu.Root>
			<ContextMenu.Trigger>
				{#snippet child({ props })}
					<tbody {...props} class="w-full border-b border-b-surface-100-900 {regionBody}">
						{#each $rows as row, rowIndex}
							{@const meta = row?.meta ?? row}
							<tr
								onclick={(e) => onRowClick(e, rowIndex)}
								onkeydown={(e) => onRowKeydown(e, rowIndex)}
								oncontextmenu={() => (contextMenuOpenRow = row)}
								aria-rowindex={rowIndex + 1}
								class="hover:preset-tonal-primary even:bg-surface-50 cursor-pointer"
							>
								{#if hasBatchActions}
									<td
										class="group/check w-10 text-center cursor-pointer"
										role="gridcell"
										onclick={(e) => {
											e.stopPropagation();
											if (meta?.id) toggleRowSelection(meta.id);
										}}
									>
										<span
											class="inline-flex items-center justify-center w-9 h-9 rounded-full transition-colors group-hover/check:bg-black/10 dark:group-hover/check:bg-white/10"
										>
											<input
												type="checkbox"
												class="checkbox pointer-events-none"
												checked={selectedIds.has(meta?.id)}
												tabindex={-1}
											/>
										</span>
									</td>
								{/if}
								{#each Object.entries(row) as [key, value]}
									{#if key !== 'meta'}
										{@const component = fieldComponentMap[key]}
										<td role="gridcell">
											<div class={regionCell}>
												{#if component && browser}
													{@const CellComponent = component}
													{#if CellComponent === LecChartPreview}
														{#key `${meta?.id || rowIndex}-${key}`}
															<CellComponent {meta} cell={value} />
														{/key}
													{:else}
														<CellComponent {meta} cell={value} />
													{/if}
												{:else}
													<div
														data-testid="model-table-td-array-elem"
														class="base-font-family whitespace-pre-line break-words"
													>
														{#if Array.isArray(value)}
															{@const hiddenCount = isRelatedField(key) ? countMasked(value) : 0}
															{@const visibleValues = isRelatedField(key)
																? value.filter((item) => !isMaskedPlaceholder(item))
																: value}
															{#if visibleValues.length > 0}
																<ul class="list-disc pl-4 whitespace-normal">
																	{#each [...visibleValues].sort((a, b) => {
																		if ((!a.str && typeof a === 'object') || (!b.str && typeof b === 'object')) return 0;
																		return safeTranslate(a.str || a).localeCompare(safeTranslate(b.str || b));
																	}) as val}
																		<li>
																			{#if key === 'linked_models' && typeof val === 'string'}
																				{safeTranslate(convertLinkedModelName(val))}
																			{:else if key === 'security_objectives' || key === 'security_capabilities'}
																				{@const [securityObjectiveName, securityObjectiveValue] =
																					Object.entries(val)[0]}
																				{safeTranslate(securityObjectiveName).toUpperCase()}: {securityObjectiveValue}
																			{:else if val.str && val.id && key !== 'qualifications' && key !== 'relationship' && key !== 'nature'}
																				{@const itemHref = `/${model?.foreignKeyFields?.find((item) => item.field === key)?.urlModel || key.replace(/_/g, '-')}/${val.id}`}
																				<Anchor href={itemHref} class="anchor" stopPropagation
																					>{safeTranslate(val.str)}</Anchor
																				>
																			{:else if val.str}
																				{safeTranslate(val.str)}
																			{:else if typeof val === 'string' && val.includes(':') && unsafeTranslate(val.split(':')[0])}
																				<span class="text"
																					>{unsafeTranslate(val.split(':')[0] + 'Colon')}
																					{val.split(':')[1]}</span
																				>
																			{:else}
																				{val ?? '-'}
																			{/if}
																		</li>
																	{/each}
																</ul>
																{#if hiddenCount > 0}
																	<p class="mt-1 text-xs text-yellow-700">
																		{m.objectsNotVisible({ count: hiddenCount })}
																	</p>
																{/if}
															{:else if hiddenCount > 0}
																<p class="text-xs text-yellow-700">
																	{m.objectsNotVisible({ count: hiddenCount })}
																</p>
															{:else}
																--
															{/if}
														{:else if isMaskedPlaceholder(value)}
															{#if isRelatedField(key)}
																<p class="text-xs text-yellow-700">
																	{m.objectsNotVisible({ count: 1 })}
																</p>
															{:else}
																--
															{/if}
														{:else if value && value.str}
															{#if value.id}
																{@const itemHref = `/${model?.foreignKeyFields?.find((item) => item.field === key)?.urlModel}/${value.id}`}
																{#if key === 'ro_to_couple'}
																	<Anchor
																		breadcrumbAction="push"
																		href={itemHref}
																		class="anchor"
																		stopPropagation
																		>{safeTranslate(toCamelCase(value.str.split(' - ')[0]))} - {value.str.split(
																			'-'
																		)[1]}</Anchor
																	>
																{:else}
																	<Anchor
																		breadcrumbAction="push"
																		href={itemHref}
																		class="anchor"
																		stopPropagation>{safeTranslate(value.str)}</Anchor
																	>
																{/if}
															{:else}
																{safeTranslate(value.str) ?? '-'}
															{/if}
														{:else if value && value.hexcolor}
															<p
																class="flex w-fit min-w-24 justify-center px-2 py-1 rounded-md ml-2 whitespace-nowrap {classesHexBackgroundText(
																	value.hexcolor
																)}"
																style="background-color: {value.hexcolor}"
															>
																{safeTranslate(value.name ?? value.str) ?? '-'}
															</p>
														{:else if ISO_8601_REGEX.test(value) && (key === 'created_at' || key === 'updated_at' || key === 'start_date' || key === 'expiry_date' || key === 'expiration_date' || key === 'accepted_at' || key === 'rejected_at' || key === 'revoked_at' || key === 'eta' || key === 'due_date' || key === 'timestamp' || key === 'reported_at' || key === 'discovered_on')}
															{formatDateOrDateTime(value, getLocale())}
														{:else if [true, false].includes(value)}
															<span class="ml-4">{safeTranslate(value ?? '-')}</span>
														{:else if key === 'progress' || key === 'treatment_progress'}
															<span class="ml-9"
																>{safeTranslate('percentageDisplay', { number: value })}</span
															>
														{:else if key === 'translations'}
															{#if Object.keys(value).length > 0}
																<div class="flex flex-col gap-2">
																	{#each Object.entries(value) as [lang, translation]}
																		<div class="flex flex-row gap-2">
																			<strong>{lang}:</strong>
																			<span>{safeTranslate(translation)}</span>
																		</div>
																	{/each}
																</div>
															{:else}
																--
															{/if}
														{:else if URLModel == 'risk-acceptances' && key === 'name' && row.meta?.accepted_at && row.meta?.revoked_at == null}
															<div class="flex items-center space-x-2">
																<span>{safeTranslate(value ?? '-')}</span>
																<span
																	class="bg-green-100 text-green-800 text-xs font-semibold mr-2 px-2.5 py-0.5 rounded-sm dark:bg-green-200 dark:text-green-900"
																>
																	{m.accept()}
																</span>
															</div>
														{:else if (key === 'name' || key === 'str') && row.meta?.is_locked}
															<div class="flex items-center space-x-2">
																<i class="fa-solid fa-lock text-yellow-600" title={m.isLocked()}
																></i>
																<span class="text-yellow-600">{safeTranslate(value ?? '-')}</span>
															</div>
														{:else if key === 'icon_fa_class'}
															<i class="text-lg fa {value}"></i>
														{:else if value && value.name}
															{value.name}
														{:else}
															<!-- NOTE: We will have to handle the ellipses for RTL languages-->
															{#if value?.length > 300}
																{safeTranslate(value ?? '-').slice(0, 300)}...
															{:else}
																{safeTranslate(value ?? '-')}
															{/if}
														{/if}
														{@render badge?.(key, row)}
													</div>
												{/if}
											</div>
										</td>
									{/if}
								{/each}
								{#if displayActions}
									<td class="text-end {regionCell}" role="gridcell">
										{#if actions}{@render actions({
												meta: row.meta
											})}{:else if row.meta[identifierField]}
											{@const actionsComponent = fieldComponentMap[CUSTOM_ACTIONS_COMPONENT]}
											<TableRowActions
												deleteForm={disableDelete ? null : deleteForm}
												{model}
												URLModel={actionsURLModel}
												detailURL={`/${actionsURLModel}/${row.meta[identifierField]}${detailQueryParameter}`}
												editURL={!(row.meta.builtin || row.meta.urn) ||
												URLModel === 'terminologies' ||
												URLModel === 'entities'
													? `/${actionsURLModel}/${row.meta[identifierField]}/edit?next=${encodeURIComponent(page.url.pathname + page.url.search)}`
													: undefined}
												{row}
												hasBody={actionsBody}
												{identifierField}
												{disableEdit}
												{disableView}
												preventDelete={preventDelete(row)}
												preventEdit={preventEdit(row)}
											>
												{#snippet head()}
													{#if actionsHead}
														{@render actionsHead?.()}
													{/if}
												{/snippet}
												{#snippet body()}
													{#if actionsBody}
														{@render actionsBody?.()}
													{/if}
												{/snippet}
												{#snippet tail()}
													{@const ActionsComponent = actionsComponent}
													{#if tail_render}{@render tail_render()}{:else if ActionsComponent}
														<ActionsComponent meta={row.meta ?? {}} {actionsURLModel} {handler} />
													{/if}
												{/snippet}
											</TableRowActions>
										{/if}
									</td>
								{/if}
							</tr>
						{/each}
					</tbody>
				{/snippet}
			</ContextMenu.Trigger>
			{#if contextMenuDisplayEdit || contextMenuDisplayDelete || Object.hasOwn(contextMenuActions, URLModel)}
				<ContextMenu.Content
					class="z-50 min-w-[180px] outline-hidden bg-white px-1 py-1.5 shadow-md border border-surface-200 rounded-md"
				>
					{#if Object.hasOwn(contextMenuActions, URLModel)}
						{#each contextMenuActions[URLModel] as action}
							<action.component row={contextMenuOpenRow} {handler} {URLModel} {action} />
						{/each}
						<ContextMenu.Separator class="-mx-1 my-1 block h-px bg-surface-100" />
					{/if}
					{#if !(contextMenuOpenRow?.meta.builtin || contextMenuOpenRow?.meta.urn) || URLModel === 'terminologies' || URLModel === 'entities'}
						<ContextMenu.Item
							class="flex h-10 w-full select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium cursor-pointer data-highlighted:bg-surface-50"
							onclick={() => {
								goto(
									`/${actionsURLModel}/${contextMenuOpenRow?.meta[identifierField]}/edit?next=${encodeURIComponent(page.url.pathname + page.url.search)}`,
									{
										breadcrumbAction: 'push'
									}
								);
							}}
						>
							{m.edit()}
						</ContextMenu.Item>
						<ContextMenu.Item
							class="flex h-10 w-full select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium cursor-pointer data-highlighted:bg-surface-50"
							onclick={() => {
								goto(`/${actionsURLModel}/${contextMenuOpenRow?.meta[identifierField]}/`, {
									breadcrumbAction: 'push'
								});
							}}
						>
							{m.view()}
						</ContextMenu.Item>
					{/if}
					{#if contextMenuDisplayDelete}
						<ContextMenu.Separator class="-mx-1 my-1 block h-px bg-surface-100" />
						<ContextMenu.Item
							class="flex h-10 w-full select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium cursor-pointer text-red-500 data-highlighted:bg-surface-50"
							onclick={() => {
								if (URLModel === 'folders') {
									contextMenuPromptModalConfirmDelete(
										contextMenuOpenRow?.meta[identifierField],
										contextMenuOpenRow
									);
								} else {
									contextMenuModalConfirmDelete(
										contextMenuOpenRow?.meta[identifierField],
										contextMenuOpenRow
									);
								}
							}}
						>
							{m.delete()}
						</ContextMenu.Item>
					{/if}
				</ContextMenu.Content>
			{/if}
		</ContextMenu.Root>
		{#if tableSource.foot}
			<tfoot class="table-foot {regionFoot}">
				<tr>
					{#each tableSource.foot as cell}
						<td class={regionFootCell}>{cell}</td>
					{/each}
				</tr>
			</tfoot>
		{/if}
	</table>

	<footer class="flex justify-between items-center space-x-8 p-2">
		{#if rowCount && pagination}
			<RowCount {handler} />
		{/if}
		{#if pagination}
			<Pagination {handler} {URLModel} />
		{/if}
	</footer>
</div>
