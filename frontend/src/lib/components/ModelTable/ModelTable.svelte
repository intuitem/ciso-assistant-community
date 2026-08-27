<script lang="ts">
	import { Popover } from '@skeletonlabs/skeleton-svelte';
	import { run } from 'svelte/legacy';

	import { goto as _goto } from '$app/navigation';
	import { page } from '$app/state';
	import TableRowActions from '$lib/components/TableRowActions/TableRowActions.svelte';
	import { booleanDisplay } from '$lib/utils/boolean-display';
	import { ISO_8601_REGEX } from '$lib/utils/constants';
	import { CUSTOM_ACTIONS_COMPONENT, getFieldComponentMap, URL_MODEL_MAP } from '$lib/utils/crud';
	import { safeTranslate, unsafeTranslate } from '$lib/utils/i18n';
	import { toCamelCase } from '$lib/utils/locales.js';
	import { onMount, tick, untrack } from 'svelte';

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
	import { tableFilterStates } from '$lib/utils/stores';
	import BatchActionBar from './BatchActionBar.svelte';
	import ColumnSelector from './ColumnSelector.svelte';
	import type { urlModel } from '$lib/utils/types.js';
	import { countMasked, isMaskedPlaceholder } from '$lib/utils/related-visibility';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	import type { SvelteEvent } from '@skeletonlabs/skeleton-svelte';
	import { DataHandler, type State } from '@vincjo/datatables/remote';
	import { defaults, superForm, type SuperValidated } from 'sveltekit-superforms';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { z } from 'zod';
	import type { FormDataShape } from '$lib/utils/schemas';
	import { loadTableData } from './handler';
	import Pagination from './Pagination.svelte';
	import RowCount from './RowCount.svelte';
	import RowsPerPage from './RowsPerPage.svelte';
	import Search from './Search.svelte';
	import Th from './Th.svelte';
	import ThFilter from './ThFilter.svelte';
	import {
		canPerformAction,
		canPerformActionOnObject,
		hasPermissionAnywhere
	} from '$lib/utils/access-control';
	import { ContextMenu } from 'bits-ui';
	import { tableHandlers, tableStates, tableColumnStates } from '$lib/utils/stores';
	import DeleteConfirmModal from '$lib/components/Modals/DeleteConfirmModal.svelte';
	import PromptConfirmModal from '$lib/components/Modals/PromptConfirmModal.svelte';
	import SaveFilterModal from '$lib/components/Modals/SaveFilterModal.svelte';
	import RenameSavedFilterModal from '$lib/components/Modals/RenameSavedFilterModal.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { getSavedFilterEligibleModels, sharedSavedFilterFolderId } from '$lib/utils/savedFilters';
	import type { SavedFilterEntry, SharedSavedFilter } from '$lib/utils/savedFilters';
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
		deleteForm?: SuperValidated<FormDataShape>;
		URLModel?: urlModel;
		baseEndpoint?: string;
		detailQueryParameter?: string;
		fields?: string[];
		columnSelector?: boolean;
		columnStateKey?: string;
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
		// Table-scoped batch actions merged into the batch bar next to the child
		// model's global batchActions. The caller pre-gates them (DetailView only
		// passes them when the user can change the parent object); this component
		// only applies the disableDelete/disableEdit filters — never the
		// child-model permission filter, which would ask the wrong question for
		// parent_action entries.
		extraBatchActions?: import('$lib/utils/table').TableBatchAction[];
	}

	let {
		source = { head: {}, body: [] },
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
		backgroundColor = 'bg-surface-50-950',
		color = '',
		regionHead = '',
		regionHeadCell = 'uppercase bg-surface-50-950 text-surface-700-300',
		regionBody = 'bg-surface-50-950',
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
		columnSelector = undefined,
		columnStateKey = undefined,
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
		tail,
		extraBatchActions = []
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

	// Column visibility & order, persisted per URLModel through the column selector.
	const allColumns = $derived(
		Object.entries(tableSource.head).map(([key, label]) => ({ key, label: label as string }))
	);
	const allColumnKeys = $derived(allColumns.map((c) => c.key));
	// A page-provided `fields` curation is the default visible set; otherwise the generic list-view default.
	const defaultColumns = $derived(
		(fields.length > 0
			? fields
			: URLModel && listViewFields[URLModel]?.body
				? listViewFields[URLModel].body
				: allColumnKeys
		).filter((key) => allColumnKeys.includes(key))
	);
	// Offered on standalone list pages, or wherever a page opts in explicitly (even alongside `fields`).
	const showColumnSelector = $derived(
		(columnSelector ?? Boolean(deleteForm)) &&
			Boolean(URLModel) &&
			(columnSelector === true || isStandaloneTable) &&
			(columnSelector === true || fields.length === 0) &&
			allColumns.length > 1
	);
	// Persistence key: distinct per embedded table when set, else the shared per-model key.
	const stateKey = $derived(columnStateKey ?? URLModel);
	// Stored choice, with stale keys dropped and a fallback to defaults so a table is never empty.
	const storedColumns = $derived(stateKey ? $tableColumnStates[stateKey] : undefined);
	const sanitizedStored = $derived(storedColumns?.filter((key) => allColumnKeys.includes(key)));
	const visibleColumns = $derived(sanitizedStored?.length ? sanitizedStored : defaultColumns);
	// Keys to render, in order. Without the selector, keep natural head order (behaviour unchanged).
	const renderColumnKeys = $derived(
		showColumnSelector
			? visibleColumns
			: allColumnKeys.filter((key) => fields.length === 0 || fields.includes(key))
	);
	$effect(() => {
		if (fields.length > 0 && allColumnKeys.length > 0 && renderColumnKeys.length === 0) {
			console.warn(
				`ModelTable(${URLModel}): none of \`fields\` [${fields.join(', ')}] match source.head keys [${allColumnKeys.join(', ')}] — table will render no columns. Build head with headData().`
			);
		}
	});

	// Order-sensitive so a pure reorder of the default set still persists instead of resetting.
	const sameAsDefault = (cols: string[]) =>
		cols.length === defaultColumns.length && cols.every((key, i) => defaultColumns[i] === key);

	function setVisibleColumns(visible: string[]) {
		if (!stateKey) return;
		if (sameAsDefault(visible)) {
			resetColumns();
			return;
		}
		$tableColumnStates = { ...$tableColumnStates, [stateKey]: visible };
	}

	function resetColumns() {
		if (!stateKey) return;
		const next = { ...$tableColumnStates };
		delete next[stateKey];
		$tableColumnStates = next;
	}

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
	const nonNavigableRelatedFields = new Set(['qualifications', 'relationship', 'nature']);
	const getRelatedFieldHref = (
		fieldName: string,
		id: string,
		options: { fallbackToDashedField?: boolean } = {}
	): string | undefined => {
		if (nonNavigableRelatedFields.has(fieldName)) return undefined;
		const relatedUrlModel = model?.foreignKeyFields?.find(
			(field) => field.field === fieldName
		)?.urlModel;
		const urlModel =
			relatedUrlModel ?? (options.fallbackToDashedField ? fieldName.replace(/_/g, '-') : undefined);

		if (!urlModel) return undefined;
		return `/${urlModel}/${id}`;
	};

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
				showColumnSelector && allColumnKeys.length > 0
					? { head: allColumnKeys, body: allColumnKeys }
					: fields.length > 0
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
	const preventEdit = (row: TableSource) => row?.meta?.builtin || forcePreventEdit;

	const tableURLModel = URLModel;

	let contextMenuOpenRow: TableSource | undefined = $state(undefined);

	const filters = $derived(source?.filters ?? tableFilters);
	const filteredFields = $derived(Object.keys(filters));
	// Only persist filters on standalone list pages, not embedded sub-tables
	const isStandaloneTable = baseEndpoint === `/${URLModel}`;
	const filterStoreKey = `${page.url.pathname}::${baseEndpoint}`;
	const storedFilters = isStandaloneTable ? ($tableFilterStates[filterStoreKey] ?? {}) : {};
	// Check if any filter-related URL params exist
	const hasUrlFilterParams = filteredFields.some(
		(field) => page.url.searchParams.getAll(field).length > 0
	);
	const filterValues: { [key: string]: any } = $state(
		Object.fromEntries(
			filteredFields.map((field: string) => {
				const urlValues = page.url.searchParams.getAll(field).map((value) => ({ value }));
				if (urlValues.length > 0) return [field, urlValues];
				// Restore persisted filters only when no URL filter params exist at all
				if (!hasUrlFilterParams && field in storedFilters) {
					return [field, storedFilters[field] ?? []];
				}
				const defaultValue = defaultFilters[field] || [];
				return [field, defaultValue];
			})
		)
	);
	$effect(() => onFilterChange(filterValues));

	// --- Saved filters --------------------------------------------------
	let savedFilterTargetModels: Record<string, string> = $state({});
	onMount(() => {
		getSavedFilterEligibleModels().then((map) => {
			savedFilterTargetModels = map;
		});
	});
	const savedFilterModel = $derived(savedFilterTargetModels[URLModel as string]);

	type AppliedSavedFilter = {
		id: string;
		scope: 'personal' | 'shared';
		properties: Record<string, { value: string }[]>;
	};

	let personalSavedFilters: SavedFilterEntry[] = $state([]);
	let sharedSavedFilters: SharedSavedFilter[] = $state([]);
	let appliedSavedFilter: AppliedSavedFilter | undefined = $state();
	const appliedSavedFilterName = $derived(
		appliedSavedFilter?.scope === 'personal'
			? personalSavedFilters.find((f) => f.id === appliedSavedFilter?.id)?.name
			: sharedSavedFilters.find((f) => f.id === appliedSavedFilter?.id)?.name
	);

	const savedFilterPickerSchema = z.object({ savedFilter: z.string().optional().nullable() });
	const savedFilterPickerForm = superForm(
		defaults({ savedFilter: null }, zod(savedFilterPickerSchema)),
		{
			SPA: true,
			dataType: 'json',
			validators: zod(savedFilterPickerSchema),
			taintedMessage: false
		}
	);
	const savedFilterOptions = $derived([
		...personalSavedFilters.map((entry) => ({
			label: entry.name,
			value: entry.id,
			suggested: true
		})),
		...sharedSavedFilters.map((entry) => ({
			label: entry.name,
			value: entry.id,
			suggested: false
		}))
	]);

	function onSavedFilterPicked(value: string) {
		if (!value) return;
		const personal = personalSavedFilters.find((f) => f.id === value);
		if (personal) {
			applySavedFilter(personal, 'personal');
		} else {
			const shared = sharedSavedFilters.find((f) => f.id === value);
			if (shared) applySavedFilter(shared, 'shared');
		}
		savedFilterPickerForm.form.update((data) => ({ ...data, savedFilter: null }));
	}

	async function loadSavedFilters() {
		if (!savedFilterModel) return;
		const [personalRes, sharedRes] = await Promise.all([
			fetch('/fe-api/saved-filters/personal/'),
			fetch('/fe-api/saved-filters/')
		]);
		if (personalRes.ok) {
			const all = (await personalRes.json()) as SavedFilterEntry[];
			personalSavedFilters = all.filter((entry) => entry.model === savedFilterModel);
		}
		if (sharedRes.ok) {
			const data = await sharedRes.json();
			const all = (data.results ?? data) as SharedSavedFilter[];
			sharedSavedFilters = all.filter((entry) => entry.model === savedFilterModel);
		}
	}

	$effect(() => {
		if (savedFilterModel) untrack(() => loadSavedFilters());
	});

	const appliedSharedFilter = $derived(
		appliedSavedFilter?.scope === 'shared'
			? sharedSavedFilters.find((f) => f.id === appliedSavedFilter!.id)
			: undefined
	);
	const canEditSharedFilter = $derived(
		!!appliedSharedFilter &&
			canPerformActionOnObject({
				user,
				action: 'change',
				model: 'savedfilter',
				object: { folder: appliedSharedFilter.folder }
			})
	);
	const canDeleteSharedFilter = $derived(
		!!appliedSharedFilter &&
			canPerformActionOnObject({
				user,
				action: 'delete',
				model: 'savedfilter',
				object: { folder: appliedSharedFilter.folder }
			})
	);

	// A shared filter's values referencing an object the current user can't
	// read come back from the backend masked as `{}` (same convention as
	// related-object masking elsewhere, see related-visibility.ts) -- those
	// criteria are dropped rather than applied as "undefined".
	function unmaskedEntries(values: { value: string }[] | undefined) {
		return (values ?? []).filter((v) => !isMaskedPlaceholder(v));
	}

	function applySavedFilter(
		entry: SavedFilterEntry | SharedSavedFilter,
		scope: 'personal' | 'shared'
	) {
		for (const field of filteredFields) {
			filterValues[field] = unmaskedEntries(entry.properties?.[field]);
		}
		// filterValues drives the URL/query; the filter widgets themselves read
		// from the SuperForm store, which must be synced separately (see resetFilters).
		_form.form.update((data) => {
			for (const field of filteredFields) {
				data[field] = unmaskedEntries(entry.properties?.[field]).map((v) => v.value);
			}
			return data;
		});
		// The baseline for unsaved-change detection must match what actually
		// landed in filterValues (masked entries dropped), not the raw stored
		// properties -- otherwise a shared filter with masked values would
		// show as "modified" right after being applied.
		appliedSavedFilter = { id: entry.id, scope, properties: { ...filterValues } };
		openState = false;
	}

	function normalizedFilterValues(values: { value: string }[] | undefined): string[] {
		return (values ?? [])
			.map((v) => v?.value)
			.filter((v): v is string => v !== undefined && v !== null && v !== '')
			.sort();
	}

	const savedFilterHasUnsavedChanges = $derived(
		!!appliedSavedFilter &&
			filteredFields.some((field) => {
				const current = normalizedFilterValues(filterValues[field]);
				const saved = normalizedFilterValues(appliedSavedFilter!.properties?.[field]);
				return current.length !== saved.length || current.some((v, i) => v !== saved[i]);
			})
	);

	async function saveAppliedFilterChanges() {
		if (!appliedSavedFilter) return;
		const endpoint =
			appliedSavedFilter.scope === 'personal'
				? `/fe-api/saved-filters/personal/${appliedSavedFilter.id}/`
				: `/fe-api/saved-filters/${appliedSavedFilter.id}/`;
		const res = await fetch(endpoint, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ properties: { ...filterValues } })
		});
		if (!res.ok) return;
		const entry = (await res.json()) as SavedFilterEntry | SharedSavedFilter;
		if (appliedSavedFilter.scope === 'personal') {
			personalSavedFilters = personalSavedFilters.map((f) =>
				f.id === entry.id ? (entry as SavedFilterEntry) : f
			);
		} else {
			sharedSavedFilters = sharedSavedFilters.map((f) =>
				f.id === entry.id ? (entry as SharedSavedFilter) : f
			);
		}
		appliedSavedFilter = {
			id: entry.id,
			scope: appliedSavedFilter.scope,
			properties: entry.properties
		};
	}

	function clearAppliedSavedFilter() {
		for (const field of filteredFields) {
			filterValues[field] = [];
		}
		_form.form.update((data) => {
			for (const field of filteredFields) {
				data[field] = [];
			}
			return data;
		});
		appliedSavedFilter = undefined;
	}

	function openSaveFilterModal() {
		const modalComponent: ModalComponent = {
			ref: SaveFilterModal,
			props: {
				model: savedFilterModel,
				properties: { ...filterValues },
				onSaved: (entry: SavedFilterEntry | SharedSavedFilter, scope: 'personal' | 'shared') => {
					if (scope === 'personal')
						personalSavedFilters = [...personalSavedFilters, entry as SavedFilterEntry];
					else sharedSavedFilters = [...sharedSavedFilters, entry as SharedSavedFilter];
					appliedSavedFilter = { id: entry.id, scope, properties: entry.properties };
				}
			}
		};
		modalStore.trigger({ type: 'component', component: modalComponent, title: m.saveFilter() });
	}

	function openEditPersonalFilterModal() {
		if (appliedSavedFilter?.scope !== 'personal') return;
		const current = personalSavedFilters.find((f) => f.id === appliedSavedFilter!.id);
		if (!current) return;
		const modalComponent: ModalComponent = {
			ref: RenameSavedFilterModal,
			props: {
				user,
				initialName: current.name,
				filterId: current.id,
				model: savedFilterModel,
				properties: { ...filterValues },
				onRenamed: async (newName: string) => {
					const res = await fetch(`/fe-api/saved-filters/personal/${appliedSavedFilter!.id}/`, {
						method: 'PATCH',
						headers: { 'Content-Type': 'application/json' },
						body: JSON.stringify({ name: newName, properties: { ...filterValues } })
					});
					if (res.ok) {
						const entry = (await res.json()) as SavedFilterEntry;
						personalSavedFilters = personalSavedFilters.map((f) => (f.id === entry.id ? entry : f));
						appliedSavedFilter = { id: entry.id, scope: 'personal', properties: entry.properties };
					}
				},
				onShared: ({
					shared,
					deletedPersonalId
				}: {
					shared: SharedSavedFilter;
					deletedPersonalId: string;
				}) => {
					sharedSavedFilters = [...sharedSavedFilters, shared];
					personalSavedFilters = personalSavedFilters.filter((f) => f.id !== deletedPersonalId);
					if (appliedSavedFilter?.id === deletedPersonalId) {
						appliedSavedFilter = { id: shared.id, scope: 'shared', properties: shared.properties };
					}
				}
			}
		};
		modalStore.trigger({ type: 'component', component: modalComponent, title: m.edit() });
	}

	async function deletePersonalFilter() {
		if (appliedSavedFilter?.scope !== 'personal') return;
		const res = await fetch(`/fe-api/saved-filters/personal/${appliedSavedFilter.id}/`, {
			method: 'DELETE'
		});
		if (res.ok || res.status === 204) {
			personalSavedFilters = personalSavedFilters.filter((f) => f.id !== appliedSavedFilter!.id);
			appliedSavedFilter = undefined;
		}
	}

	function openEditSharedFilterModal() {
		if (appliedSavedFilter?.scope !== 'shared') return;
		const current = sharedSavedFilters.find((f) => f.id === appliedSavedFilter!.id);
		if (!current) return;
		const modalComponent: ModalComponent = {
			ref: RenameSavedFilterModal,
			props: {
				initialName: current.name,
				currentDomainId: sharedSavedFilterFolderId(current.folder),
				onRenamed: async (newName: string, newDomain?: string) => {
					const res = await fetch(`/fe-api/saved-filters/${appliedSavedFilter!.id}/`, {
						method: 'PATCH',
						headers: { 'Content-Type': 'application/json' },
						body: JSON.stringify({
							name: newName,
							properties: { ...filterValues },
							...(newDomain ? { folder: newDomain } : {})
						})
					});
					if (res.ok) {
						const entry = (await res.json()) as SharedSavedFilter;
						sharedSavedFilters = sharedSavedFilters.map((f) => (f.id === entry.id ? entry : f));
						appliedSavedFilter = { id: entry.id, scope: 'shared', properties: entry.properties };
					}
				}
			}
		};
		modalStore.trigger({ type: 'component', component: modalComponent, title: m.edit() });
	}

	async function deleteSharedFilter() {
		if (appliedSavedFilter?.scope !== 'shared') return;
		const res = await fetch(`/fe-api/saved-filters/${appliedSavedFilter.id}/`, {
			method: 'DELETE'
		});
		if (res.ok || res.status === 204) {
			sharedSavedFilters = sharedSavedFilters.filter((f) => f.id !== appliedSavedFilter!.id);
			appliedSavedFilter = undefined;
		}
	}
	// --- End saved filters -----------------------------------------------

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
		}
		history.replaceState(history.state, '', page.url.pathname + page.url.search);
		// Sync the current crumb's href with the new filter query.
		breadcrumbs.update((crumbs) => {
			if (crumbs.length < 2) return crumbs;
			const last = crumbs[crumbs.length - 1];
			const lastPath = last.href?.split('?')[0];
			if (lastPath !== page.url.pathname) return crumbs;
			const newHref = page.url.pathname + page.url.search;
			if (last.href === newHref) return crumbs;
			const next = crumbs.slice();
			next[next.length - 1] = { ...last, href: newHref };
			return next;
		});
		// untracked so resetFilters can delete the entry without retriggering us
		if (isStandaloneTable) {
			untrack(() => {
				$tableFilterStates[filterStoreKey] = { ...filterValues };
			});
		}
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
				: hasPermissionAnywhere(user, `add_${model.name}`)
			: false
	);
	let contextMenuCanEditObject = $derived(
		(model
			? canPerformActionOnObject({
					user,
					action: 'change',
					model: model.name,
					object: contextMenuOpenRow?.meta
				})
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
		!preventDelete(contextMenuOpenRow ?? { head: {}, body: [], meta: [] }) &&
			(model
				? canPerformActionOnObject({
						user,
						action: 'delete',
						model: model.name,
						object: contextMenuOpenRow?.meta
					})
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

	async function resetFilters() {
		for (const field of filteredFields) {
			const defaultValue = defaultFilters[field] ?? [];
			filterValues[field] = Array.isArray(defaultValue)
				? defaultValue.map((v: { value: string }) => ({ ...v }))
				: [];
		}
		_form.form.update((data) => {
			for (const field of filteredFields) {
				const dv = defaultFilters[field];
				data[field] = Array.isArray(dv) ? dv.map((v: any) => v.value ?? v) : [];
			}
			return data;
		});
		// Resetting the criteria invalidates whatever saved filter was applied --
		// its name would otherwise stay shown next to now-unrelated values.
		appliedSavedFilter = undefined;
		if (!isStandaloneTable) return;
		await tick();
		const next = { ...$tableFilterStates };
		delete next[filterStoreKey];
		$tableFilterStates = next;
	}

	let classesHexBackgroundText = $derived((backgroundHexColor: string) => {
		// The badge background is a fixed hex color, so the text must be a fixed color too
		// (not theme-dependent), otherwise it turns light in dark mode and vanishes on a
		// light-colored badge. White on dark backgrounds, fixed dark surface otherwise.
		return isDark(backgroundHexColor) ? 'text-white' : 'text-surface-950';
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
		return (
			MULTI_VALUE_COLUMNS.includes(key) ||
			(tableSource.body.length > 0 && Array.isArray(tableSource.body[0][key]))
		);
	};

	// Helper function to convert linked_models snake_case to camelCase for translation
	const convertLinkedModelName = (snakeCaseName: string): string => {
		const mapping: Record<string, string> = {
			// Validation flows
			compliance_assessments: 'complianceAssessments',
			risk_assessments: 'riskAssessments',
			business_impact_analysis: 'businessImpactAnalysis',
			crq_studies: 'quantitativeRiskStudies',
			ebios_studies: 'ebiosRMStudies',
			entity_assessments: 'entityAssessments',
			findings_assessments: 'findingsAssessments',
			evidences: 'evidences',
			security_exceptions: 'securityExceptions',
			policies: 'policies',
			// Applied controls
			requirement_assessments: 'requirementAssessments',
			risk_scenarios: 'riskScenarios',
			risk_scenarios_e: 'riskScenariosExisting',
			findings: 'findings',
			vulnerabilities: 'vulnerabilities',
			stakeholders: 'stakeholders',
			processings: 'processings',
			data_breaches_remediated: 'dataBreaches',
			quantitative_risk_hypotheses_existing: 'crqHypothesesExisting',
			quantitative_risk_hypotheses_added: 'crqHypothesesAdded',
			quantitative_risk_hypotheses_removed: 'crqHypothesesRemoved',
			assetassessment: 'assetAssessments',
			task_templates: 'taskTemplates',
			comments: 'comments'
		};
		return mapping[snakeCaseName] || snakeCaseName;
	};

	let openState = $state(false);

	// Search state lifted here so it survives BatchActionBar show/hide cycles
	let searchValue = $state('');

	// Batch selection state
	let selectedIds: Set<string> = $state(new Set());

	const currentBatchActions: BatchActionConfig[] = $derived(
		URLModel && model
			? getBatchActions(URLModel).filter((a) =>
					a.type === 'delete'
						? !disableDelete && hasPermissionAnywhere(user, `delete_${model.name}`)
						: !disableEdit && hasPermissionAnywhere(user, `change_${model.name}`)
				)
			: []
	);
	// Table-scoped extras are pre-gated by the caller (change on the parent);
	// only the lock/disable filters apply here — the child-model permission
	// filter above would ask the wrong question for parent_action entries.
	const extraActions = $derived(
		extraBatchActions.filter((a) => (a.type === 'delete' ? !disableDelete : !disableEdit))
	);
	const allBatchActions = $derived([...currentBatchActions, ...extraActions]);
	const hasBatchActions = $derived(
		(currentBatchActions.length > 0 && deleteForm !== undefined) || extraActions.length > 0
	);

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

	let tableWrapEl: HTMLElement | undefined = $state();
</script>

<div class="card table-wrap {classesBase}" bind:this={tableWrapEl}>
	<header class="flex items-center justify-between gap-2 px-2 h-16">
		{#if hasBatchActions && selectedIds.size > 0}
			<BatchActionBar
				{selectedIds}
				actions={allBatchActions}
				{URLModel}
				{handler}
				onClearSelection={clearSelection}
			/>
		{:else}
			{#if !hideFilters}
				<div class="flex items-center gap-2">
					<Popover
						open={openState}
						onOpenChange={(e) => (openState = e.open)}
						positioning={{ placement: 'bottom-start' }}
						autoFocus={false}
						onPointerDownOutside={() => (openState = false)}
						closeOnInteractOutside={false}
					>
						<Popover.Trigger class="btn preset-filled-primary-500 h-9 inline-flex items-center">
							<i class="fa-solid fa-filter mr-2"></i>
							{m.filters()}
							{#if filterCount}
								<span class="text-sm">{filterCount}</span>
							{/if}
						</Popover.Trigger>
						<Popover.Positioner class="z-50!">
							<Popover.Content
								class="card p-2 bg-surface-50-950 max-w-lg shadow-lg space-y-2 border border-surface-200-800"
							>
								{#if savedFilterModel}
									<div class="space-y-1 pb-2 mb-2 border-b border-surface-200-800">
										<p class="text-xs font-semibold text-surface-500 px-1">{m.savedFilters()}</p>
										{#if appliedSavedFilter}
											<div
												class="space-y-1 px-2 py-1 rounded bg-surface-100-900 text-sm font-semibold"
											>
												<div class="flex items-center justify-between gap-1">
													<span class="truncate">{appliedSavedFilterName}</span>
													<div class="flex items-center gap-1 flex-shrink-0">
														{#if savedFilterHasUnsavedChanges && (appliedSavedFilter.scope === 'personal' || canEditSharedFilter)}
															<button
																type="button"
																class="text-surface-500 hover:text-surface-700-300"
																title={m.save()}
																onclick={() => saveAppliedFilterChanges()}
															>
																<i class="fa-solid fa-floppy-disk"></i>
															</button>
														{/if}
														<button
															type="button"
															class="text-surface-500 hover:text-surface-700-300"
															title={m.clearSelection()}
															onclick={() => clearAppliedSavedFilter()}
														>
															<i class="fa-solid fa-xmark"></i>
														</button>
													</div>
												</div>
												<div class="flex items-center gap-2">
													{#if appliedSavedFilter.scope === 'personal'}
														<button
															type="button"
															class="btn btn-sm preset-tonal-surface"
															onclick={() => openEditPersonalFilterModal()}
														>
															<i class="fa-solid fa-pen mr-1"></i>{m.edit()}
														</button>
														<button
															type="button"
															class="btn btn-sm preset-tonal-surface"
															onclick={() => deletePersonalFilter()}
														>
															<i class="fa-solid fa-trash mr-1"></i>{m.delete()}
														</button>
													{:else}
														{#if canEditSharedFilter}
															<button
																type="button"
																class="btn btn-sm preset-tonal-surface"
																onclick={() => openEditSharedFilterModal()}
															>
																<i class="fa-solid fa-pen mr-1"></i>{m.edit()}
															</button>
														{/if}
														{#if canDeleteSharedFilter}
															<button
																type="button"
																class="btn btn-sm preset-tonal-surface"
																onclick={() => deleteSharedFilter()}
															>
																<i class="fa-solid fa-trash mr-1"></i>{m.delete()}
															</button>
														{/if}
													{/if}
												</div>
											</div>
										{:else if personalSavedFilters.length === 0 && sharedSavedFilters.length === 0}
											<p class="text-sm text-surface-500 px-2 py-1">{m.noSavedFilters()}</p>
										{:else}
											<AutocompleteSelect
												form={savedFilterPickerForm}
												field="savedFilter"
												options={savedFilterOptions}
												onChange={(value) => onSavedFilterPicked(value)}
											/>
										{/if}
									</div>
								{/if}
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
															(v) => v !== null && v !== undefined && v !== ''
														);

														filterValues[field] = sanitizedArrayValue.map((v) => ({ value: v }));
													}}
												/>
											{/if}
										{/each}
										{#if filterCount > 0}
											<div class="flex justify-end pt-1">
												<button
													type="button"
													class="btn preset-tonal-surface text-sm"
													onclick={() => {
														resetFilters();
														openState = false;
													}}
												>
													<i class="fa-solid fa-rotate-left mr-2"></i>
													{m.resetFilters()}
												</button>
											</div>
										{/if}
									{/snippet}
								</SuperForm>
							</Popover.Content>
						</Popover.Positioner>
					</Popover>
					{#if savedFilterModel}
						{#if appliedSavedFilter}
							<div
								class="flex items-center justify-between px-2 py-1 rounded bg-surface-100-900 text-sm font-semibold"
							>
								<span>{appliedSavedFilterName}</span>
								<button
									type="button"
									class="text-surface-500 hover:text-surface-700-300"
									title={m.clearSelection()}
									onclick={() => clearAppliedSavedFilter()}
								>
									<i class="fa-solid fa-xmark"></i>
								</button>
							</div>
						{/if}
						{#if !appliedSavedFilter && filterCount > 0}
							<button
								type="button"
								class="btn preset-tonal-surface h-9"
								title={m.saveFilter()}
								onclick={() => openSaveFilterModal()}
							>
								<i class="fa-solid fa-floppy-disk text-surface-700-300"></i>
							</button>
						{/if}
					{/if}
				</div>
			{/if}

			{#if search}
				<Search {handler} bind:value={searchValue} />
			{/if}
			{#if pagination && rowsPerPage}
				<RowsPerPage {handler} />
			{/if}
			{#if showColumnSelector}
				<ColumnSelector
					columns={allColumns}
					visible={visibleColumns}
					onChange={setVisibleColumns}
					onReset={resetColumns}
				/>
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
							class="inline-flex items-center justify-center w-9 h-9 rounded-full transition-colors group-hover/check:bg-black/10 dark:group-hover/check:bg-surface-100-900/10"
						>
							<input
								type="checkbox"
								class="checkbox pointer-events-none"
								aria-label={m.selectAll()}
								checked={selectAllChecked}
								tabindex={-1}
							/>
						</span>
					</th>
				{/if}
				{#each renderColumnKeys as key (key)}
					<Th {handler} orderBy={isMultiValueColumn(key) ? undefined : key} class={regionHeadCell}
						>{safeTranslate(tableSource.head[key])}</Th
					>
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
					{#each renderColumnKeys as key (key)}
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
								class="hover:bg-surface-200-800 even:bg-surface-100-900 cursor-pointer"
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
											class="inline-flex items-center justify-center w-9 h-9 rounded-full transition-colors group-hover/check:bg-black/10 dark:group-hover/check:bg-surface-100-900/10"
										>
											<input
												type="checkbox"
												class="checkbox pointer-events-none"
												aria-label={m.selectRow()}
												checked={selectedIds.has(meta?.id)}
												tabindex={-1}
											/>
										</span>
									</td>
								{/if}
								{#each renderColumnKeys as key (key)}
									{@const value = row[key]}
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
																		{:else if val.str && val.id}
																			{@const itemHref = getRelatedFieldHref(key, val.id, {
																				fallbackToDashedField: true
																			})}
																			{#if itemHref}
																				<Anchor href={itemHref} class="anchor" stopPropagation
																					>{safeTranslate(val.str)}</Anchor
																				>
																			{:else}
																				{safeTranslate(val.str)}
																			{/if}
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
														{@const itemHref = value.id
															? getRelatedFieldHref(key, value.id)
															: undefined}
														{#if itemHref}
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
													{:else if ISO_8601_REGEX.test(value) && (key === 'created_at' || key === 'updated_at' || key === 'start_date' || key === 'end_date' || key === 'expiry_date' || key === 'expiration_date' || key === 'accepted_at' || key === 'rejected_at' || key === 'revoked_at' || key === 'eta' || key === 'due_date' || key === 'timestamp' || key === 'reported_at' || key === 'discovered_on')}
														{formatDateOrDateTime(value, getLocale())}
													{:else if [true, false].includes(value)}
														{@const bd = booleanDisplay(value, key, URLModel)}
														<span class="ml-4"><i class="{bd.icon} {bd.colorClass}"></i></span>
													{:else if value === 'YES' || value === 'NO'}
														{@const bd = booleanDisplay(value === 'YES', key, URLModel)}
														<span class="ml-4"><i class="{bd.icon} {bd.colorClass}"></i></span>
													{:else if key === 'progress' || key === 'treatment_progress' || key === 'progress_field'}
														<span class="ml-9"
															>{value != null
																? safeTranslate('percentageDisplay', { number: value })
																: '--'}</span
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
													{:else if URLModel == 'risk-acceptances' && key === 'name' && row.meta?.state}
														<div class="flex items-center space-x-2">
															<span>{safeTranslate(value ?? '-')}</span>
															<span
																class="badge text-xs"
																class:preset-tonal-success={row.meta.state === 'Accepted'}
																class:preset-tonal-error={row.meta.state === 'Rejected' ||
																	row.meta.state === 'Revoked'}
																class:preset-tonal-primary={row.meta.state === 'Submitted'}
																class:preset-tonal-secondary={row.meta.state === 'Created'}
															>
																{row.meta.state === 'Created'
																	? m.draft()
																	: safeTranslate(row.meta.state)}
															</span>
														</div>
													{:else if (key === 'name' || key === 'str') && row.meta?.is_locked}
														<div class="flex items-center space-x-2">
															<i class="fa-solid fa-lock text-yellow-600" title={m.isLocked()}></i>
															<span class="text-yellow-600">{safeTranslate(value ?? '-')}</span>
														</div>
													{:else if key === 'icon_fa_class'}
														<i class="text-lg fa {value}"></i>
													{:else if value && value.name}
														{value.name}
													{:else}
														<!-- NOTE: We will have to handle the ellipses for RTL languages-->
														{@const displayValue = [
															'name',
															'description',
															'ref_id',
															'key'
														].includes(key)
															? (value ?? '-')
															: safeTranslate(value ?? '-')}
														{#if displayValue?.length > 300}
															{displayValue.slice(0, 300)}...
														{:else}
															{displayValue}
														{/if}
													{/if}
													{@render badge?.(key, row)}
												</div>
											{/if}
										</div>
									</td>
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
					class="z-50 min-w-[180px] outline-hidden bg-surface-50-950 px-1 py-1.5 shadow-md border border-surface-200-800 rounded-md"
				>
					{#if Object.hasOwn(contextMenuActions, URLModel)}
						{#each contextMenuActions[URLModel] as action}
							<action.component row={contextMenuOpenRow} {handler} {URLModel} {action} />
						{/each}
						<ContextMenu.Separator class="-mx-1 my-1 block h-px bg-surface-100-900" />
					{/if}
					{#if !(contextMenuOpenRow?.meta.builtin || contextMenuOpenRow?.meta.urn) || URLModel === 'terminologies' || URLModel === 'entities'}
						<ContextMenu.Item
							class="flex h-10 w-full select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium cursor-pointer data-highlighted:bg-surface-100-900"
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
							class="flex h-10 w-full select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium cursor-pointer data-highlighted:bg-surface-100-900"
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
						<ContextMenu.Separator class="-mx-1 my-1 block h-px bg-surface-100-900" />
						<ContextMenu.Item
							class="flex h-10 w-full select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium cursor-pointer text-red-500 data-highlighted:bg-surface-100-900"
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
			<Pagination {handler} {URLModel} scrollTarget={tableWrapEl} />
		{/if}
	</footer>
</div>
