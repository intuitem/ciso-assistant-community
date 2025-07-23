<script lang="ts">
	import { Popover } from '@skeletonlabs/skeleton-svelte';
	import { run } from 'svelte/legacy';

	import { goto as _goto, afterNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import TableRowActions from '$lib/components/TableRowActions/TableRowActions.svelte';
	import { ISO_8601_REGEX } from '$lib/utils/constants';
	import { CUSTOM_ACTIONS_COMPONENT, FIELD_COMPONENT_MAP, URL_MODEL_MAP } from '$lib/utils/crud';
	import { safeTranslate, unsafeTranslate } from '$lib/utils/i18n';
	import { toCamelCase } from '$lib/utils/locales.js';
	import { onMount } from 'svelte';

	import { tableA11y } from '$lib/components/ModelTable/actions';
	// Types
	import { browser } from '$app/environment';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import type { TableSource } from '$lib/components/ModelTable/types';
	import { goto } from '$lib/utils/breadcrumbs';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { isDark } from '$lib/utils/helpers';
	import { contextMenuActions, listViewFields } from '$lib/utils/table';
	import type { urlModel } from '$lib/utils/types.js';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	import { type SvelteEvent } from '@skeletonlabs/skeleton-svelte';
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
	import { canPerformAction } from '$lib/utils/access-control';
	import { ContextMenu } from 'bits-ui';
	import { tableHandlers, tableStates } from '$lib/utils/stores';

	interface Props {
		// Props
		source?: TableSource;
		interactive?: boolean;
		search?: boolean;
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
		hideFilters?: boolean;
		folderId?: string;
		forcePreventDelete?: boolean;
		forcePreventEdit?: boolean;
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
		regionCell = 'max-w-[65ch] text-ellipsis',
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
		hideFilters = $bindable(false),
		folderId = '',
		forcePreventDelete = false,
		forcePreventEdit = false,
		optButton,
		selectButton,
		addButton,
		badge,
		actions,
		actionsBody,
		actionsHead,
		tail
	}: Props = $props();

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
		goto(`/${URLModel}/${rowMetaData[identifierField]}${detailQueryParameter}`, {
			label:
				rowMetaData.str ??
				rowMetaData.name ??
				rowMetaData.email ??
				rowMetaData.label ??
				rowMetaData[identifierField],
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

	// Replace $$props.class with classProp for compatibility
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
				: 0, // Using 0 as rowsPerPage value when pagination is false disables paging.
			totalRows: source?.meta?.count
		}
	);
	const rows = handler.getRows();
	let invalidateTable = $state(true);

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
		(row?.meta?.builtin && actionsURLModel !== 'loaded-libraries') ||
		(!URLModel?.includes('libraries') && Object.hasOwn(row?.meta, 'urn') && row?.meta?.urn) ||
		(URLModel?.includes('campaigns') && row?.meta?.compliance_assessments.length > 0) ||
		(Object.hasOwn(row?.meta, 'reference_count') && row?.meta?.reference_count > 0) ||
		['severity_changed', 'status_changed'].includes(row?.meta?.entry_type) ||
		forcePreventDelete;
	const preventEdit = (row: TableSource) => forcePreventEdit;

	const tableURLModel = URLModel;

	let contextMenuOpenRow: TableSource | undefined = $state(undefined);

	const filters =
		tableURLModel &&
		listViewFields[tableURLModel] &&
		Object.hasOwn(listViewFields[tableURLModel], 'filters')
			? listViewFields[tableURLModel].filters
			: {};

	const filteredFields = Object.keys(filters);
	const filterValues: { [key: string]: any } = $state(
		Object.fromEntries(
			filteredFields.map((field: string) => [
				field,
				page.url.searchParams.getAll(field).map((value) => ({ value }))
			])
		)
	);

	run(() => {
		hideFilters = hideFilters || !Object.entries(filters).some(([_, filter]) => !filter.hide);
	});

	$effect(() => {
		for (const field of filteredFields) {
			handler.filter(
				filterValues[field] ? filterValues[field].map((v: Record<string, any>) => v.value) : [],
				field
			);
			page.url.searchParams.delete(field);
			if (filterValues[field] && filterValues[field].length > 0) {
				for (const value of filterValues[field]) {
					page.url.searchParams.append(field, value.value);
				}
			}
		}
	});

	const filterInitialData: Record<string, string[]> = {};
	// convert URL search params to filter initial data
	for (const [key, value] of page.url.searchParams) {
		filterInitialData[key] ??= [];
		filterInitialData[key].push(value);
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

	$effect(() => {
		if (invalidateTable) {
			console.debug('Invalidating table due to filter change');
			handler.invalidate();
			_goto(page.url);
			invalidateTable = false;
		}
	});

	let field_component_map = $derived(FIELD_COMPONENT_MAP[URLModel] ?? {});
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
			: false) && !(contextMenuOpenRow?.meta.builtin || contextMenuOpenRow?.meta.urn)
	);

	let contextMenuDisplayEdit = $derived(
		contextMenuCanEditObject &&
			URLModel &&
			!['frameworks', 'risk-matrices', 'ebios-rm'].includes(URLModel)
	);
	let filterCount = $derived(
		filteredFields.reduce((acc, field) => acc + filterValues[field].length, 0)
	);

	let classesHexBackgroundText = $derived((backgroundHexColor: string) => {
		return isDark(backgroundHexColor) ? 'text-white' : '';
	});

	const tail_render = $derived(tail);

	let openState = $state(false);
</script>

<div class="table-wrap {classesBase}">
	<header class="flex justify-between items-center space-x-8 p-2">
		{#if !hideFilters}
			<Popover
				open={openState}
				onOpenChange={(e) => (openState = e.open)}
				positioning={{ placement: 'bottom-start' }}
				triggerBase="btn preset-filled-primary-500 self-end relative"
				contentBase="card p-2 bg-white max-w-lg shadow-lg space-y-2 border border-surface-200"
				zIndex="1000"
				autoFocus={false}
				onPointerDownOutside={() => (openState = false)}
				closeOnInteractOutside={false}
			>
				{#snippet trigger()}
					<i class="fa-solid fa-filter mr-2"></i>
					{m.filters()}
					{#if filterCount}
						<span class="text-sm">{filterCount}</span>
					{/if}
				{/snippet}
				{#snippet content()}
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
											filterValues[field] = value.map((v) => ({ value: v }));
											invalidateTable = true;
										}}
									/>
								{/if}
							{/each}
						{/snippet}
					</SuperForm>
				{/snippet}
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
	</header>
	<!-- Table -->
	<table
		class="table caption-bottom {classesTable}"
		class:table-interactive={interactive}
		role="grid"
		use:tableA11y
	>
		<thead class="table-head {regionHead}">
			<tr>
				{#each Object.entries(tableSource.head) as [key, heading]}
					{#if fields.length === 0 || fields.includes(key)}
						<Th {handler} orderBy={key} class={regionHeadCell}>{safeTranslate(heading)}</Th>
					{/if}
				{/each}
				{#if displayActions}
					<th class="{regionHeadCell} select-none text-end"></th>
				{/if}
			</tr>
		</thead>
		<ContextMenu.Root>
			<tbody class="table-body w-full border-b border-b-surface-100-900 {regionBody}">
				{#each $rows as row, rowIndex}
					{@const meta = row?.meta ?? row}
					<ContextMenu.Trigger asChild>
						{#snippet children({ builder })}
							<tr
								use:builder.action
								{...builder}
								onclick={(e) => {
									onRowClick(e, rowIndex);
								}}
								onkeydown={(e) => {
									onRowKeydown(e, rowIndex);
								}}
								oncontextmenu={() => (contextMenuOpenRow = row)}
								aria-rowindex={rowIndex + 1}
								class="hover:preset-tonal-primary even:bg-surface-50 cursor-pointer"
							>
								{#each Object.entries(row) as [key, value]}
									{#if key !== 'meta'}
										{@const component = field_component_map[key]}
										<td class={regionCell} role="gridcell">
											{#if component && browser}
												{@const CellComponent = component}
												<CellComponent {meta} cell={value} />
											{:else}
												<span class="base-font-family whitespace-pre-line break-words">
													{#if Array.isArray(value)}
														<ul class="list-disc pl-4 whitespace-normal">
															{#each value as val}
																<li>
																	{#if val.str && val.id}
																		{@const itemHref = `/${model?.foreignKeyFields?.find((item) => item.field === key)?.urlModel || key}/${val.id}`}
																		<Anchor href={itemHref} class="anchor" stopPropagation
																			>{val.str}</Anchor
																		>
																	{:else if val.str}
																		{safeTranslate(val.str)}
																	{:else if unsafeTranslate(val.split(':')[0])}
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
													{:else if value && value.str}
														{#if value.id}
															{@const itemHref = `/${model?.foreignKeyFields?.find((item) => item.field === key)?.urlModel}/${value.id}`}
															{#if key === 'ro_to_couple'}
																<Anchor breadcrumbAction="push" href={itemHref} class="anchor"
																	>{safeTranslate(toCamelCase(value.str.split(' - ')[0]))} - {value.str.split(
																		'-'
																	)[1]}</Anchor
																>
															{:else}
																<Anchor breadcrumbAction="push" href={itemHref} class="anchor"
																	>{value.str}</Anchor
																>
															{/if}
														{:else}
															{value.str ?? '-'}
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
													{:else if ISO_8601_REGEX.test(value) && (key === 'created_at' || key === 'updated_at' || key === 'expiry_date' || key === 'accepted_at' || key === 'rejected_at' || key === 'revoked_at' || key === 'eta' || key === 'timestamp')}
														{formatDateOrDateTime(value, getLocale())}
													{:else if [true, false].includes(value)}
														<span class="ml-4">{safeTranslate(value ?? '-')}</span>
													{:else if key === 'progress'}
														<span class="ml-9"
															>{safeTranslate('percentageDisplay', { number: value })}</span
														>
													{:else if URLModel == 'risk-acceptances' && key === 'name' && row.meta?.accepted_at && row.meta?.revoked_at == null}
														<div class="flex items-center space-x-2">
															<span>{safeTranslate(value ?? '-')}</span>
															<span
																class="bg-green-100 text-green-800 text-xs font-semibold mr-2 px-2.5 py-0.5 rounded-sm dark:bg-green-200 dark:text-green-900"
															>
																{m.accept()}
															</span>
														</div>
													{:else if key === 'icon_fa_class'}
														<i class="text-lg fa {value}"></i>
													{:else}
														<!-- NOTE: We will have to handle the ellipses for RTL languages-->
														{#if value?.length > 300}
															{safeTranslate(value ?? '-').slice(0, 300)}...
														{:else}
															{safeTranslate(value ?? '-')}
														{/if}
													{/if}
													{@render badge?.(key, row)}
												</span>
											{/if}
										</td>
									{/if}
								{/each}
								{#if displayActions}
									<td class="text-end {regionCell}" role="gridcell">
										{#if actions}{@render actions({
												meta: row.meta
											})}{:else if row.meta[identifierField]}
											{@const actionsComponent = field_component_map[CUSTOM_ACTIONS_COMPONENT]}
											{@const actionsURLModel = URLModel}
											<TableRowActions
												deleteForm={disableDelete ? null : deleteForm}
												{model}
												URLModel={actionsURLModel}
												detailURL={`/${actionsURLModel}/${row.meta[identifierField]}${detailQueryParameter}`}
												editURL={!(row.meta.builtin || row.meta.urn)
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
						{/snippet}
					</ContextMenu.Trigger>
				{/each}
			</tbody>
			{#if contextMenuDisplayEdit || Object.hasOwn(contextMenuActions, URLModel)}
				<ContextMenu.Content
					class="z-50 w-full max-w-[229px] outline-hidden card bg-white px-1 py-1.5 shadow-md cursor-default"
				>
					{#if Object.hasOwn(contextMenuActions, URLModel)}
						{#each contextMenuActions[URLModel] as action}
							<action.component row={contextMenuOpenRow} {handler} {URLModel} {action} />
						{/each}
						<ContextMenu.Separator class="-mx-1 my-1 block h-px bg-surface-100" />
					{/if}
					{#if !(contextMenuOpenRow?.meta.builtin || contextMenuOpenRow?.meta.urn)}
						<ContextMenu.Item
							class="flex h-10 select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! data-highlighted:bg-surface-50"
						>
							<Anchor
								href={`/${actionsURLModel}/${contextMenuOpenRow?.meta[identifierField]}/edit?next=${encodeURIComponent(page.url.pathname + page.url.search)}`}
								class="flex items-cente w-full h-full cursor-default outline-hidden ring-0! ring-transparent!"
								>{m.edit()}</Anchor
							>
						</ContextMenu.Item>
					{/if}
					<!-- {#if !preventDelete(contextMenuOpenRow ?? { head: [], body: [], meta: [] })} -->
					<!-- 	<ContextMenu.Item -->
					<!-- 		class="flex h-10 select-none items-center rounded-xs py-3 pl-3 pr-1.5 text-sm font-medium outline-hidden ring-0! ring-transparent! data-highlighted:bg-surface-50" -->
					<!-- 	> -->
					<!-- 		<div class="flex items-center w-full h-full">{m.delete()}</div> -->
					<!-- 	</ContextMenu.Item> -->
					<!-- {/if} -->
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
			<Pagination {handler} />
		{/if}
	</footer>
</div>
