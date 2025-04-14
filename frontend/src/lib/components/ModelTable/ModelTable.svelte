<script lang="ts">
	import { goto as _goto } from '$app/navigation';
	import { page } from '$app/stores';
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
	import { listViewFields } from '$lib/utils/table';
	import type { urlModel } from '$lib/utils/types.js';
	import { m } from '$paraglide/messages';
	import { getLocale } from '$paraglide/runtime';
	import {
		popup,
		type CssClasses,
		type PopupSettings,
		type SvelteEvent
	} from '@skeletonlabs/skeleton';
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

	// Props
	export let source: TableSource = { head: [], body: [] };
	export let interactive = true;

	export let search = true;
	export let rowsPerPage = true;
	export let rowCount = true;
	export let pagination = true;
	export let numberRowsPerPage = 10;

	export let orderBy: { identifier: string; direction: 'asc' | 'desc' } | undefined = undefined;

	// Props (styles)
	export let element: CssClasses = 'table';
	export let text: CssClasses = 'text-xs';
	export let backgroundColor: CssClasses = 'bg-white';
	export let color: CssClasses = '';
	export let regionHead: CssClasses = '';
	export let regionHeadCell: CssClasses = 'uppercase bg-white text-gray-700';
	export let regionBody: CssClasses = 'bg-white';
	export let regionCell: CssClasses = '';
	export let regionFoot: CssClasses = '';
	export let regionFootCell: CssClasses = '';

	export let displayActions = true;

	export let identifierField = 'id';
	export let deleteForm: SuperValidated<AnyZodObject> | undefined = undefined;
	export let URLModel: urlModel | undefined = undefined;
	export let baseEndpoint: string = `/${URLModel}`;
	export let detailQueryParameter: string | undefined = undefined;
	export let fields: string[] = [];
	export let canSelectObject = false;

	export let hideFilters = false;

	export let folderId: string = '';

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
				rowMetaData.str ?? rowMetaData.name ?? rowMetaData.email ?? rowMetaData[identifierField],
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

	const user = $page.data.user;

	// Replace $$props.class with classProp for compatibility
	let classProp = ''; // Replacing $$props.class

	$: classesBase = `${classProp || backgroundColor}`;
	$: classesTable = `${element} ${text} ${color}`;

	const handler = new DataHandler(
		source.body.map((item: Record<string, any>, index: number) => {
			return {
				...item,
				meta: source.meta
					? source.meta.results
						? { ...source.meta.results[index] }
						: { ...source.meta[index] }
					: undefined
			};
		}),
		{
			rowsPerPage: pagination ? numberRowsPerPage : undefined,
			totalRows: source.meta.count
		}
	);
	const rows = handler.getRows();
	let invalidateTable = false;

	handler.onChange((state: State) =>
		loadTableData({ state, URLModel, endpoint: baseEndpoint, fields })
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
		(row.meta.builtin && actionsURLModel !== 'loaded-libraries') ||
		(!URLModel?.includes('libraries') && Object.hasOwn(row.meta, 'urn') && row.meta.urn) ||
		(Object.hasOwn(row.meta, 'reference_count') && row.meta.reference_count > 0) ||
		['severity_changed', 'status_changed'].includes(row.meta.entry_type);

	const filterInitialData = $page.url.searchParams.entries();

	const _form = superForm(defaults(filterInitialData, zod(z.object({}))), {
		SPA: true,
		validators: zod(z.object({})),
		dataType: 'json',
		invalidateAll: false,
		applyAction: false,
		resetForm: false,
		taintedMessage: false,
		validationMethod: 'auto'
	});

	const popupFilter: PopupSettings = {
		event: 'click',
		target: 'popupFilter',
		placement: 'bottom-start'
	};

	const tableURLModel = URLModel;
	const filters =
		tableURLModel && Object.hasOwn(listViewFields[tableURLModel], 'filters')
			? listViewFields[tableURLModel].filters
			: {};

	const filteredFields = Object.keys(filters);
	const filterValues: { [key: string]: any } = {};

	// Initialize filter values from URL search params
	for (const field of filteredFields)
		filterValues[field] = $page.url.searchParams.getAll(field).map((value) => ({ value }));

	$: hideFilters = hideFilters || !Object.entries(filters).some(([_, filter]) => !filter.hide);

	$: {
		for (const field of filteredFields) {
			handler.filter(
				filterValues[field] ? filterValues[field].map((v: Record<string, any>) => v.value) : [],
				field
			);
			$page.url.searchParams.delete(field);
			if (filterValues[field] && filterValues[field].length > 0) {
				for (const value of filterValues[field]) {
					$page.url.searchParams.append(field, value.value);
				}
			}
		}
		if (browser || invalidateTable) {
			handler.invalidate();
			_goto($page.url);
			invalidateTable = false;
		}
	}

	$: field_component_map = FIELD_COMPONENT_MAP[URLModel] ?? {};
	$: model = URL_MODEL_MAP[URLModel];
	$: canCreateObject = model
		? $page.params.id
			? canPerformAction({
					user,
					action: 'add',
					model: model.name,
					domain:
						folderId ||
						$page.data?.data?.folder?.id ||
						$page.data?.data?.folder ||
						$page.params.id ||
						user.root_folder_id
				})
			: Object.hasOwn(user.permissions, `add_${model.name}`)
		: false;
	$: filterCount = filteredFields.reduce((acc, field) => acc + filterValues[field].length, 0);

	$: classesHexBackgroundText = (backgroundHexColor: string) => {
		return isDark(backgroundHexColor) ? 'text-white' : '';
	};
</script>

<div class="table-container {classesBase}">
	<header class="flex justify-between items-center space-x-8 p-2">
		{#if !hideFilters}
			<button
				use:popup={popupFilter}
				class="btn variant-filled-primary self-end relative"
				id="filters"
			>
				<i class="fa-solid fa-filter mr-2" />
				{m.filters()}
				{#if filterCount}
					<span class="badge absolute -top-0 -right-0 z-10">{filterCount}</span>
				{/if}
			</button>
			<div
				class="card p-2 bg-white max-w-lg shadow-lg space-y-2 border border-surface-200"
				data-popup="popupFilter"
			>
				<SuperForm {_form} validators={zod(z.object({}))} let:form>
					{#each filteredFields as field}
						{#if filters[field]?.component}
							<svelte:component
								this={filters[field].component}
								{form}
								{field}
								{...filters[field].props}
								fieldContext="filter"
								label={safeTranslate(filters[field].props?.label)}
								on:change={(e) => {
									const value = e.detail;
									filterValues[field] = value.map((v) => ({ value: v }));
									invalidateTable = true;
								}}
							/>
						{/if}
					{/each}
				</SuperForm>
			</div>
		{/if}
		{#if search}
			<Search {handler} />
		{/if}
		{#if pagination && rowsPerPage}
			<RowsPerPage {handler} />
		{/if}
		<div class="flex space-x-2 items-center">
			<slot name="optButton" />
			{#if canSelectObject}
				<slot name="selectButton" />
			{/if}
			{#if canCreateObject}
				<slot name="addButton" />
			{/if}
		</div>
	</header>
	<!-- Table -->
	<table
		class="w-full {classesTable}"
		class:table-interactive={interactive}
		role="grid"
		use:tableA11y
	>
		<thead class="table-head {regionHead}">
			<tr>
				{#each Object.entries(source.head) as [key, heading]}
					<Th {handler} orderBy={key} class={regionHeadCell}>{safeTranslate(heading)}</Th>
				{/each}
				{#if displayActions}
					<th class="{regionHeadCell} select-none text-end"></th>
				{/if}
			</tr>
		</thead>
		<tbody class="table-body {regionBody}">
			{#each $rows as row, rowIndex}
				{@const meta = row?.meta ?? row}
				<tr
					on:click={(e) => {
						onRowClick(e, rowIndex);
					}}
					on:keydown={(e) => {
						onRowKeydown(e, rowIndex);
					}}
					aria-rowindex={rowIndex + 1}
				>
					{#each Object.entries(row) as [key, value]}
						{#if key !== 'meta'}
							{@const component = field_component_map[key]}
							<td class={regionCell} role="gridcell">
								{#if component}
									<svelte:component this={component} {meta} cell={value} />
								{:else}
									<span class="font-token whitespace-pre-line break-words">
										{#if Array.isArray(value)}
											<ul class="list-disc pl-4 whitespace-normal">
												{#each value as val}
													<li>
														{#if val.str && val.id}
															{@const itemHref = `/${URL_MODEL_MAP[URLModel]['foreignKeyFields']?.find((item) => item.field === key)?.urlModel || key}/${val.id}`}
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
												{@const itemHref = `/${URL_MODEL_MAP[URLModel]['foreignKeyFields']?.find((item) => item.field === key)?.urlModel}/${value.id}`}
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
													class="bg-green-100 text-green-800 text-xs font-semibold mr-2 px-2.5 py-0.5 rounded dark:bg-green-200 dark:text-green-900"
												>
													{m.accept()}
												</span>
											</div>
										{:else}
											<!-- NOTE: We will have to handle the ellipses for RTL languages-->
											{#if value?.length > 300}
												{safeTranslate(value ?? '-').slice(0, 300)}...
											{:else}
												{safeTranslate(value ?? '-')}
											{/if}
										{/if}
									</span>
								{/if}
							</td>
						{/if}
					{/each}
					{#if displayActions}
						<td class="text-end {regionCell}" role="gridcell">
							<slot name="actions" meta={row.meta}>
								{#if row.meta[identifierField]}
									{@const actionsComponent = field_component_map[CUSTOM_ACTIONS_COMPONENT]}
									{@const actionsURLModel = URLModel}
									<TableRowActions
										{deleteForm}
										{model}
										URLModel={actionsURLModel}
										detailURL={`/${actionsURLModel}/${row.meta[identifierField]}${detailQueryParameter}`}
										editURL={!(row.meta.builtin || row.meta.urn)
											? `/${actionsURLModel}/${row.meta[identifierField]}/edit?next=${encodeURIComponent($page.url.pathname + $page.url.search)}`
											: undefined}
										{row}
										hasBody={$$slots.actionsBody}
										{identifierField}
										preventDelete={preventDelete(row)}
									>
										<svelte:fragment slot="head">
											{#if $$slots.actionsHead}
												<slot name="actionsHead" />
											{/if}
										</svelte:fragment>
										<svelte:fragment slot="body">
											{#if $$slots.actionsBody}
												<slot name="actionsBody" />
											{/if}
										</svelte:fragment>
										<slot slot="tail" name="tail">
											<svelte:component
												this={actionsComponent}
												meta={row.meta ?? {}}
												{actionsURLModel}
											/>
										</slot>
									</TableRowActions>
								{/if}
							</slot>
						</td>
					{/if}
				</tr>
			{/each}
		</tbody>
		{#if source.foot}
			<tfoot class="table-foot {regionFoot}">
				<tr>
					{#each source.foot as cell}
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
