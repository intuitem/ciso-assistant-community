<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData } from './$types';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import { superForm } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';
	import { modelSchema } from '$lib/utils/schemas';
	import * as m from '$paraglide/messages.js';
	import { safeTranslate } from '$lib/utils/i18n';
	import TimelineEntryForm from '$lib/components/Forms/ModelForm/TimelineEntryForm.svelte';
	import { createModalCache } from '$lib/utils/stores';
	import { DataHandler, type State } from '@vincjo/datatables/remote';
	import { loadTableData } from '$lib/components/ModelTable/handler';
	import Search from '$lib/components/ModelTable/Search.svelte';
	import RowsPerPage from '$lib/components/ModelTable/RowsPerPage.svelte';
	import RowCount from '$lib/components/ModelTable/RowCount.svelte';
	import Pagination from '$lib/components/ModelTable/Pagination.svelte';
	import { listViewFields } from '$lib/utils/table';
	import { browser } from '$app/environment';
	import { goto as _goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { formatDateOrDateTime } from '$lib/utils/datetime';
	import { getLocale } from '$paraglide/runtime.js';
	import TableRowActions from '$lib/components/TableRowActions/TableRowActions.svelte';

	export let data: PageData;
	let invalidateAll = true;
	let formAction = '?/create';
	let context = 'create';
	const form = data.relatedModels['timeline-entries'].createForm;
	const model = data.relatedModels['timeline-entries'];
	let schema = modelSchema('timeline-entries');

	const _form = superForm(form, {
		dataType: 'json',
		enctype: 'application/x-www-form-urlencoded',
		invalidateAll,
		applyAction: $$props.applyAction ?? true,
		resetForm: $$props.resetForm ?? false,
		validators: zod(schema),
		taintedMessage: m.taintedFormMessage(),
		validationMethod: 'auto'
	});

	const source = data.relatedModels['timeline-entries'].table;
	const pagination = true;
	const numberRowsPerPage = 10;

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
	const field = data.model.reverseForeignKeyFields.find(
		(item) => item.urlModel === 'timeline-entries'
	);
	handler.onChange((state: State) =>
		loadTableData({
			state,
			URLModel: 'timeline-entries',
			endpoint: `/timeline-entries?incident=${data.data.id}`,
			fields: listViewFields['timeline-entries'].body.filter((v) => v !== field.field)
		})
	);
	let invalidateTable = false;
	$: {
		if (browser || invalidateTable) {
			handler.invalidate();
			_goto($page.url);
			invalidateTable = false;
		}
	}

	const preventDelete = (row: TableSource) =>
		['severity_changed', 'status_changed'].includes(row.meta.entry_type);
</script>

<div class="flex flex-col space-y-2">
	<DetailView {data} displayModelTable={false}>
		<div slot="widgets">
            <h1 class="text-2xl font-bold">{m.addTimelineEntry()}</h1>
			<SuperForm
				class="flex flex-col space-y-3"
				action={formAction}
				dataType={'json'}
				enctype={'application/x-www-form-urlencoded'}
				data={form}
				{_form}
				{invalidateAll}
				let:form
				let:data
				let:initialData
				validators={zod(schema)}
				onUpdated={() => createModalCache.deleteCache(model.urlModel)}
				{...$$restProps}
			>
				<TimelineEntryForm {form} {model} {initialData} {context} />
				<div class="flex flex-row justify-between space-x-4">
                    <button
						class="btn variant-filled-tertiary font-semibold w-full"
						data-testid="reset-button"
						type="button"
						on:click={() => _form.reset()}>{m.cancel()}</button
					>
					<button
						class="btn variant-filled-primary font-semibold w-full"
						data-testid="save-button"
						type="submit">{m.save()}</button
					>
				</div>
			</SuperForm>
		</div>
	</DetailView>

	<div class="card shadow-lg bg-white p-4 space-y-2">
		<div class="flex flex-row justify-between items-center">
			<h1 class="text-xl font-bold">{m.timeline()}</h1>
			<Search {handler} />
			<RowsPerPage {handler} />
		</div>
		<ol class="relative border-s border-primary-500 dark:border-primary-700">
			{#each $rows as row, rowIndex}
				{@const meta = row?.meta ?? row}
				{@const actionsURLModel = 'timeline-entries'}
				<li class="mb-5 ms-4">
					<div
						class="absolute w-3 h-3 bg-primary-500 rounded-full mt-1.5 -start-1.5 border border-white dark:border-primary-900 dark:bg-primary-700"
					></div>
					<div class="flex flex-col">
						<div class="flex flex-row items-center space-x-2">
							<time class="mb-1 text-sm font-normal leading-none text-gray-400 dark:text-gray-500"
								>{safeTranslate(meta.entry_type)} - {formatDateOrDateTime(
									meta.timestamp,
									getLocale()
								)} - {meta.author.str}</time
							>
							<TableRowActions
								baseClass="space-x-2 whitespace-nowrap flex flex-row items-center text-sm text-surface-700"
								deleteForm={data.relatedModels['timeline-entries'].deleteForm}
								model={model.info}
								URLModel={actionsURLModel}
								detailURL={`/${actionsURLModel}/${meta.id}`}
								editURL={`/${actionsURLModel}/${meta.id}/edit?next=${encodeURIComponent($page.url.pathname + $page.url.search)}`}
								{row}
								hasBody={$$slots.actionsBody}
								identifierField={'id'}
								preventDelete={preventDelete(row)}
							></TableRowActions>
                            {#if formatDateOrDateTime(meta.updated_at, getLocale()) !== formatDateOrDateTime(meta.created_at, getLocale())}
                                <span class="text-xs italic text-gray-500 dark:text-gray-400">
                                    ({m.edited()})
                                </span>
                            {/if}
						</div>
						<span class="text-primary-700 text-sm"></span>
						<span class="font-semibold text-sm">{safeTranslate(meta.entry)}</span>
						<p class="text-xs italic text-gray-500 dark:text-gray-400">
							{meta.observation ?? m.noObservation()}
						</p>
					</div>
				</li>
			{/each}
		</ol>
		<footer class="flex justify-between items-center space-x-8 p-2">
			{#if pagination}
				<RowCount {handler} />
			{/if}
			{#if pagination}
				<Pagination {handler} />
			{/if}
		</footer>
	</div>
</div>
