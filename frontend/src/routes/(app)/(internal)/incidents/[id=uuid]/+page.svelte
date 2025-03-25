<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData } from './$types';
    import SuperForm from '$lib/components/Forms/Form.svelte';
    import { superForm } from 'sveltekit-superforms';
    import { zod } from 'sveltekit-superforms/adapters';
    import { modelSchema } from '$lib/utils/schemas';
    import * as m from '$paraglide/messages.js';
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

	export let data: PageData;
	let invalidateAll = true;
	let formAction = '?/create';
	let context = 'create';
    const form = data.relatedModels['timeline-entries'].createForm
    const model = data.relatedModels['timeline-entries']
    let schema = modelSchema('timeline-entries');

    const _form = superForm(form, {
		dataType: 'json',
		enctype: 'application/x-www-form-urlencoded',
		invalidateAll,
		applyAction: $$props.applyAction ?? true,
		resetForm: $$props.resetForm ?? false,
		validators: zod(schema),
		taintedMessage: m.taintedFormMessage(),
		validationMethod: 'auto',
	});

    const source = data.relatedModels['timeline-entries'].table;
    const pagination = source.meta.pagination;
    const numberRowsPerPage = pagination ? pagination.rowsPerPage : undefined;

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
    const field = data.model.reverseForeignKeyFields.find((item) => item.urlModel === 'timeline-entries')
    handler.onChange((state: State) =>
		loadTableData({ state, URLModel: 'timeline-entries', endpoint: `/timeline-entries?incident=${data.data.id}`, fields: listViewFields['timeline-entries'].body.filter((v) => v !== field.field) })
	);
    let invalidateTable = false;
    $: {
		if (browser || invalidateTable) {
			handler.invalidate();
			_goto($page.url);
			invalidateTable = false;
		}
	}
</script>

<div class="flex flex-col space-y-2">
    <DetailView {data} displayModelTable={false}>
        <div slot="widgets">
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
               <TimelineEntryForm
                    {form}
                    {model}
                    {initialData}
                    {context}
                />
                <div class="flex flex-row justify-between space-x-4">
                    <button
                        class="btn variant-filled-primary font-semibold w-full"
                        data-testid="save-button"
                        type="submit">{m.save()}</button
                    >
                </div>
            </SuperForm>
        </div>
    </DetailView>
    
    <div class="card shadow-lg bg-white p-4">
        <Search {handler} />
        <RowsPerPage {handler} />
        {#each $rows as row, rowIndex}
				{@const meta = row?.meta ?? row}
                {#each Object.entries(row) as [key, value]}
                    {key} {value}
                {/each}
        {/each}
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
