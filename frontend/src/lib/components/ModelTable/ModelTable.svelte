<script lang="ts">
	import { page } from '$app/stores';
	import TableRowActions from '$lib/components/TableRowActions/TableRowActions.svelte';
	import {
		CUSTOM_ACTIONS_COMPONENT,
		FIELD_COLORED_TAG_MAP,
		FIELD_COMPONENT_MAP
	} from '$lib/utils/crud';
	import { stringify } from '$lib/utils/helpers';
	import { safeTranslate, unsafeTranslate } from '$lib/utils/i18n';
	import { toCamelCase } from '$lib/utils/locales.js';
	import { createEventDispatcher, onMount } from 'svelte';

	import { tableA11y } from './actions';
	// Types
	import { ISO_8601_REGEX } from '$lib/utils/constants';
	import type { urlModel } from '$lib/utils/types.js';
	import * as m from '$paraglide/messages';
	import { languageTag } from '$paraglide/runtime';
	import type { CssClasses, SvelteEvent } from '@skeletonlabs/skeleton';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';
	import type { TableSource } from './types';
	// Event Dispatcher
	type TableEvent = {
		selected: string[];
	};
	const dispatch = createEventDispatcher<TableEvent>();

	// Props
	export let source: TableSource;
	export let interactive = true;

	export let search = true;
	export let rowsPerPage = true;
	export let rowCount = true;
	export let pagination = true;
	export let numberRowsPerPage = 10;
	export let thFiler = false;

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

	export let identifierField = 'id';
	export let deleteForm: SuperValidated<AnyZodObject> | undefined = undefined;
	export let URLModel: urlModel | undefined = undefined;
	export let detailQueryParameter: string | undefined = undefined;
	detailQueryParameter = detailQueryParameter ? `?${detailQueryParameter}` : '';

	export let hideFilters = false;
	$: hideFilters =
		hideFilters ||
		!Object.entries(filters).some(([key, filter]) => {
			if (!filter.hide) return true;
		});

	const user = $page.data.user;

	$: canCreateObject = user?.permissions && Object.hasOwn(user.permissions, `add_${model?.name}`);

	import { URL_MODEL_MAP } from '$lib/utils/crud';
	import { listViewFields } from '$lib/utils/table';

	// Replace $$props.class with classProp for compatibility
	let classProp = ''; // Replacing $$props.class

	$: classesBase = `${classProp || backgroundColor}`;
	$: classesTable = `${element} ${text} ${color}`;

	import { goto as _goto } from '$app/navigation';
	import { goto } from '$lib/utils/breadcrumbs';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { DataHandler } from '@vincjo/datatables';
	import Pagination from './Pagination.svelte';
	import RowCount from './RowCount.svelte';
	import RowsPerPage from './RowsPerPage.svelte';
	import Search from './Search.svelte';
	import Th from './Th.svelte';
	import ThFilter from './ThFilter.svelte';

	$: data = source.body.map((item: Record<string, any>, index: number) => {
		return { ...item, meta: source.meta ? { ...source.meta[index] } : undefined };
	});
	const columnFields = new Set(source.body.length === 0 ? [] : Object.keys(source.body[0]));

	const handler = new DataHandler(data, {
		rowsPerPage: pagination ? numberRowsPerPage : undefined
	});
	$: hasRows = data.length > 0;
	const tableURLModel = source.meta?.urlmodel ?? URLModel;
	const filters =
		tableURLModel && Object.hasOwn(listViewFields[tableURLModel], 'filters')
			? listViewFields[tableURLModel].filters
			: {};
	const filteredFields = Object.keys(filters).filter(
		(key) => columnFields.has(key) || filters[key].alwaysDisplay
	);
	const filterValues: { [key: string]: any } = {};
	const filterProps: {
		[key: string]: { [key: string]: any };
	} = {};

	function defaultFilterProps(rows, field: string) {
		const getColumn = filters[field].getColumn ?? ((row) => row[field]);
		const options = [...new Set(rows.map(getColumn))].sort();
		return { options };
	}

	function defaultFilterFunction(entry: any, value: any[]): boolean {
		if (!value || value.length < 1) return true;
		value = value.map((v) => stringify(v));
		return value.includes(stringify(entry));
	}

	// Initialize filter values from URL search params
	for (const field of filteredFields)
		filterValues[field] = $page.url.searchParams.getAll(field).map((value) => ({ value }));

	$: {
		for (const field of filteredFields) {
			handler.filter(
				filterValues[field] ? filterValues[field].map((v) => v.value) : [],
				Object.hasOwn(filters, field) && Object.hasOwn(filters[field], 'getColumn')
					? filters[field].getColumn
					: field,
				Object.hasOwn(filters, field) && Object.hasOwn(filters[field], 'filter')
					? filters[field].filter
					: defaultFilterFunction
			);
			$page.url.searchParams.delete(field);
			if (filterValues[field] && filterValues[field].length > 0) {
				for (const value of filterValues[field]) {
					$page.url.searchParams.append(field, value.value);
				}
			}
		}
		if (browser) _goto($page.url);
	}

	$: {
		for (const key of filteredFields) {
			filterProps[key] = (filters[key].filterProps ?? defaultFilterProps)(
				Object.values(source.meta),
				key
			);
		}
	}
	const rows = handler.getRows();
	const _filters = handler.getFilters();

	function getFilterCount(filters: typeof $_filters): number {
		return Object.values(filters).reduce((acc, filter) => {
			if (Array.isArray(filter.value) && filter.value.length > 0) {
				return acc + 1;
			}
			return acc;
		}, 0);
	}

	$: filterCount = getFilterCount($_filters);

	onMount(() => {
		if (orderBy) {
			orderBy.direction === 'asc'
				? handler.sortAsc(orderBy.identifier)
				: handler.sortDesc(orderBy.identifier);
		}
	});

	$: field_component_map = FIELD_COMPONENT_MAP[URLModel] ?? {};

	const tagMap = FIELD_COLORED_TAG_MAP[URLModel] ?? {};
	const taggedKeys = new Set(Object.keys(tagMap));

	$: model = source.meta?.urlmodel ? URL_MODEL_MAP[source.meta.urlmodel] : URL_MODEL_MAP[URLModel];
	$: source, handler.setRows(data);

	const actionsURLModel = source.meta?.urlmodel ?? URLModel;
	const preventDelete = (row: TableSource) =>
		(row.meta.builtin && actionsURLModel !== 'loaded-libraries') ||
		(URLModel !== 'libraries' && Object.hasOwn(row.meta, 'urn') && row.meta.urn) ||
		(Object.hasOwn(row.meta, 'reference_count') && row.meta.reference_count > 0);

	import { isDark } from '$lib/utils/helpers';
	import type { PopupSettings } from '@skeletonlabs/skeleton';
	import { popup } from '@skeletonlabs/skeleton';
	import { browser } from '$app/environment';
	import Anchor from '$lib/components/Anchor/Anchor.svelte';

	const popupFilter: PopupSettings = {
		event: 'focus-click',
		target: 'popupFilter',
		placement: 'bottom-start',
		closeQuery: 'li'
	};

	$: classesHexBackgroundText = (backgroundHexColor: string) => {
		return isDark(backgroundHexColor) ? 'text-white' : '';
	};
</script>

<div class="table-container {classesBase}">
	<header class="flex justify-between items-center space-x-8 p-2">
		{#if filteredFields.length > 0 && hasRows && !hideFilters}
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
				{#each filteredFields as field}
					<svelte:component
						this={filters[field].component}
						bind:value={filterValues[field]}
						bind:hide={filters[field].hide}
						{field}
						{...filterProps[field]}
						{...filters[field].extraProps}
					/>
				{/each}
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
			{#if thFiler}
				<tr>
					{#each Object.keys(source.head) as key}
						<ThFilter class={regionHeadCell} {handler} filterBy={key} />
					{/each}
					{#if displayActions}
						<th class="{regionHeadCell} select-none"></th>
					{/if}
				</tr>
			{/if}
		</thead>
		<tbody class="table-body {regionBody}">
			{#each $rows as row, rowIndex}
				{@const meta = row.meta ? row.meta : row}
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
															{@const itemHref = `/${URL_MODEL_MAP[URLModel]['foreignKeyFields']?.find((item) => item.field === key)?.urlModel}/${val.id}`}
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
										{:else if ISO_8601_REGEX.test(value) && (key === 'created_at' || key === 'updated_at' || key === 'publication_date' || key === 'expiry_date' || key === 'accepted_at' || key === 'rejected_at' || key === 'revoked_at' || key === 'eta')}
											{formatDateOrDateTime(value, languageTag())}
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
											{safeTranslate(value ?? '-')}
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
									{@const actionsURLModel = source.meta.urlmodel ?? URLModel}
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
										<svelte:fragment slot="tail">
											<svelte:component
												this={actionsComponent}
												meta={row.meta ?? {}}
												{actionsURLModel}
											/>
										</svelte:fragment>
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
