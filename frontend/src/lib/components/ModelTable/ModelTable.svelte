<script lang="ts">
	import { page } from '$app/stores';
	import TableRowActions from '$lib/components/TableRowActions/TableRowActions.svelte';
	import { FIELD_COLORED_TAG_MAP, FIELD_COMPONENT_MAP } from '$lib/utils/crud';
	import { createEventDispatcher, onMount } from 'svelte';

	import { tableA11y } from './actions';
	// Types
	import type { urlModel } from '$lib/utils/types.js';
	import type { CssClasses, SvelteEvent } from '@skeletonlabs/skeleton';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { AnyZodObject } from 'zod';
	import type { TableSource } from './types';
	import * as m from '$paraglide/messages';
	import { localItems, toCamelCase } from '$lib/utils/locales';
	import { languageTag } from '$paraglide/runtime';
	import { ISO_8601_REGEX } from '$lib/utils/constants';
	// Event Dispatcher
	type TableEvent = {
		selected: string[];
	};
	const dispatch = createEventDispatcher<TableEvent>();

	// Props
	/**
	 * Provide the full set of table source data.
	 * @type {TableSource}
	 */
	export let source: TableSource;
	/** Enables row hover style and `on:selected` event when rows are clicked. */
	export let interactive = true;

	export let search = true;
	export let rowsPerPage = true;
	export let rowCount = true;
	export let pagination = true;
	export let numberRowsPerPage = 10;
	export let thFiler = false;
	export let tags = true;

	export let orderBy: { identifier: string; direction: 'asc' | 'desc' } | undefined = undefined;

	// Props (styles)
	/** Override the Tailwind Element class. Replace this for a headless UI. */
	export let element: CssClasses = 'table';
	/** Provide classes to set the table text size. */
	export let text: CssClasses = 'text-xs';
	/** Provide classes to set the table text color. */
	export let color: CssClasses = '';
	/** Provide arbitrary classes for the table head. */
	export let regionHead: CssClasses = '';
	/** Provide arbitrary classes for the table head cells. */
	export let regionHeadCell: CssClasses = 'uppercase bg-white text-gray-700';
	/** Provide arbitrary classes for the table body. */
	export let regionBody: CssClasses = 'bg-white';
	/** Provide arbitrary classes for the table cells. */
	export let regionCell: CssClasses = '';
	/** Provide arbitrary classes for the table foot. */
	export let regionFoot: CssClasses = '';
	/** Provide arbitrary classes for the table foot cells. */
	export let regionFootCell: CssClasses = '';

	export let displayActions = true;

	function onRowClick(
		event: SvelteEvent<MouseEvent | KeyboardEvent, HTMLTableRowElement>,
		rowIndex: number
	): void {
		if (!interactive) return;
		event.preventDefault();
		event.stopPropagation();
		// Prefer meta row info if available, else fallback to body row info
		const rowMetaData = $rows[rowIndex].meta;
		/** @event {rowMetaData} selected - Fires when a table row is clicked. */
		if (!rowMetaData[identifierField] || !URLModel) return;
		goto(`/${URLModel}/${rowMetaData[identifierField]}${detailQueryParameter}`);
	}

	// Row Keydown Handler
	function onRowKeydown(
		event: SvelteEvent<KeyboardEvent, HTMLTableRowElement>,
		rowIndex: number
	): void {
		if (['Enter', 'Space'].includes(event.code)) onRowClick(event, rowIndex);
	}

	export let identifierField = 'id';
	export let deleteForm: SuperValidated<AnyZodObject> | undefined = undefined;
	export let URLModel: urlModel | undefined = undefined;
	export let detailQueryParameter: string | undefined;
	detailQueryParameter = detailQueryParameter ? `?${detailQueryParameter}` : '';

	const user = $page.data.user;

	$: canCreateObject = Object.hasOwn(user.permissions, `add_${model?.name}`);

	import { URL_MODEL_MAP } from '$lib/utils/crud';

	// Reactive
	$: classesBase = `${$$props.class || 'bg-white'}`;
	$: classesTable = `${element} ${text} ${color}`;

	import { goto } from '$app/navigation';
	import { DataHandler } from '@vincjo/datatables';
	import Pagination from './Pagination.svelte';
	import RowCount from './RowCount.svelte';
	import RowsPerPage from './RowsPerPage.svelte';
	import Search from './Search.svelte';
	import Th from './Th.svelte';
	import ThFilter from './ThFilter.svelte';
	import { formatDateOrDateTime } from '$lib/utils/datetime';

	$: data = source.body.map((item: Record<string, any>, index: number) => {
		return { ...item, meta: source.meta ? { ...source.meta[index] } : undefined };
	});

	const handler = new DataHandler(data, {
		rowsPerPage: pagination ? numberRowsPerPage : undefined
	});
	const rows = handler.getRows();

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
		(Object.hasOwn(row.meta, 'reference_count') && row.meta.reference_count > 0);
</script>

<div class="table-container {classesBase}">
	<header class="flex justify-between items-center space-x-8 p-2">
		{#if search}
			<Search {handler} />
		{/if}
		{#if pagination && rowsPerPage}
			<RowsPerPage {handler} />
		{/if}
		{#if canCreateObject}
			<slot name="addButton" />
		{/if}
	</header>
	<!-- Table -->
	<!-- prettier-ignore -->
	<table
		class="w-full {classesTable}"
		class:table-interactive={interactive}
		role="grid"
		use:tableA11y
	>
		<!-- Head -->
		<thead class="table-head {regionHead}">
			<tr>
				{#each Object.entries(source.head) as [key, heading]}
					<Th {handler} orderBy={key} class="{regionHeadCell}">{localItems(languageTag())[heading]}</Th>
				{/each}
        {#if displayActions}
        <th class="{regionHeadCell} select-none text-end"></th>
        {/if}
			</tr>
      {#if thFiler}
        <tr>
        {#each Object.keys(source.head) as key}
            <ThFilter class="{regionHeadCell}" {handler} filterBy={key} />
        {/each}
          {#if displayActions}
          <th class="{regionHeadCell} select-none"></th>
          {/if}
        </tr>
      {/if}
		</thead>
		<!-- Body -->
		<tbody class="table-body {regionBody}">
			{#each $rows as row, rowIndex}
				{@const meta = row.meta ? row.meta : row}
				<!-- Row -->
				<!-- prettier-ignore -->
				<tr
					on:click={(e) => { onRowClick(e, rowIndex); }}
					on:keydown={(e) => { onRowKeydown(e, rowIndex); }}
					aria-rowindex={rowIndex + 1}
				>
					{#each Object.entries(row) as [key, value]}
            {#if key !== 'meta'}
						{@const component = field_component_map[key]}
						<!-- Cell -->
						<!-- prettier-ignore -->
						<td
							class="{regionCell}"
							role="gridcell"
						>
							{#if taggedKeys.has(key)}
								{@const _tagList = tagMap[key]}
								{@const tagList = Array.isArray(_tagList) ? _tagList : [_tagList]}
								{#each tagList as tag}
									{@const tagData = tag.values[meta[tag.key]]}
									{#if tagData && tags}
										{@const {text, cssClasses} = tagData}
										<span class={cssClasses}>
											{localItems(languageTag())[text]}
										</span>
									{/if}
								{/each}
							{/if}
							{#if component}
								<svelte:component this={component} meta={row.meta ?? {}} cell={value}/>
							{:else}
                <span class="font-token whitespace-pre-line break-words">
                {#if Array.isArray(value)}
                  <ul class="list-disc pl-4 whitespace-normal">
                    {#each value as val}
                      <li>
                        {#if val.str && val.id}
                          {@const itemHref = `/${
                            URL_MODEL_MAP[URLModel]['foreignKeyFields']?.find(
                              (item) => item.field === key
                            )?.urlModel
                          }/${val.id}`}
                          <a href={itemHref} class="anchor" on:click={e => e.stopPropagation()}>{val.str}</a>
                        {:else}
                          {val}
                        {/if}
                      </li>
                    {/each}
                  </ul>
                {:else if value && value.str}
                  {#if value.id}
                    {@const itemHref = `/${URL_MODEL_MAP[URLModel]['foreignKeyFields']?.find(
                      (item) => item.field === key
                    )?.urlModel}/${value.id}`}
                    <a href={itemHref} class="anchor" on:click={e => e.stopPropagation()}>{value.str ?? '-'}</a>
                  {:else}
                    {value.str ?? '-'}
                  {/if}
                {:else if value && value.hexcolor}
                  <p class="flex w-fit min-w-24 justify-center px-2 py-1 rounded-md ml-2 whitespace-nowrap" style="background-color: {value.hexcolor}">
					{#if localItems(languageTag())[toCamelCase(value.name ?? value.str ?? '-')]}
						{localItems(languageTag())[toCamelCase(value.name ?? value.str ?? '-')]}
					{:else}
						{value.name ?? value.str ?? '-'}
					{/if}
				</p>
				{:else if ISO_8601_REGEX.test(value)}
									{formatDateOrDateTime(value, languageTag())}
                {:else}
					{#if localItems(languageTag())[toCamelCase(value)]}
						{localItems(languageTag())[toCamelCase(value)]}
					{:else}
						{value ?? '-'}
					{/if}
                {/if}
                </span>
							{/if}
						</td>
            {/if}
					{/each}
        {#if displayActions}
						<td
							class="text-end {regionCell}"
							role="gridcell"
						>
            <slot name="actions" meta={row.meta}>
            {#if row.meta[identifierField]}
              {@const actionsComponent = field_component_map['actions']}
              {@const actionsURLModel = source.meta.urlmodel ?? URLModel}
              <TableRowActions
                deleteForm={deleteForm}
                {model}
                URLModel={actionsURLModel}
                detailURL={`/${actionsURLModel}/${row.meta[identifierField]}${detailQueryParameter}`}
                editURL={!(row.meta.builtin || row.meta.urn) ? `/${actionsURLModel}/${row.meta[identifierField]}/edit?next=${$page.url.pathname}` : undefined}
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
                  <svelte:component this={actionsComponent} meta={row.meta ?? {}} {actionsURLModel}/>
                </svelte:fragment>
              </TableRowActions>
            {/if}
            </slot>
            </td>
            {/if}
				</tr>
			{/each}
		</tbody>
		<!-- Foot -->
		{#if source.foot}
			<tfoot class="table-foot {regionFoot}">
				<tr>
					{#each source.foot as cell }
						<td class="{regionFootCell}">{cell}</td>
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
