<script lang="ts">
	import DetailView from '$lib/components/DetailView/DetailView.svelte';
	import type { PageData, ActionData } from './$types';
	import SuperForm from '$lib/components/Forms/Form.svelte';
	import { superForm } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';
	import { modelSchema } from '$lib/utils/schemas';
	import * as m from '$paraglide/messages.js';
	import { safeTranslate } from '$lib/utils/i18n';
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
	import Select from '$lib/components/Forms/Select.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import {
		type TableSource,
		type ModalComponent,
		type ModalSettings,
		type ModalStore
	} from '@skeletonlabs/skeleton';
	import { getModalStore } from '@skeletonlabs/skeleton';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';

	import { canPerformAction } from '$lib/utils/access-control';

	export let data: PageData;
	export let form: ActionData;

	const invalidateAll = true;
	const formAction = '?/create';
	const timelineForm = data.relatedModels['timeline-entries'].createForm;
	const model = data.relatedModels['timeline-entries'];
	const schema = modelSchema('timeline-entries');

	const _form = superForm(timelineForm, {
		dataType: 'json',
		enctype: 'application/x-www-form-urlencoded',
		invalidateAll,
		applyAction: $$props.applyAction ?? true,
		resetForm: true,
		validators: zod(schema),
		taintedMessage: false,
		validationMethod: 'auto',
		onUpdated: () => {
			createModalCache.deleteCache(model.urlModel);
			_form.form.update((current) => ({
				...current,
				evidences: undefined,
				timestamp: new Date().toISOString()
			}));
			refreshKey = !refreshKey;
		}
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
	$: if (browser || invalidateTable) {
		handler.invalidate();
		_goto($page.url);
		invalidateTable = false;
	}

	const preventDelete = (row: TableSource) =>
		['severity_changed', 'status_changed'].includes(row.meta.entry_type);

	const modalStore: ModalStore = getModalStore();

	function modalEvidenceCreateForm(): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: data.evidenceCreateForm,
				formAction: '?/createEvidence',
				model: data.evidenceModel,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: safeTranslate('add-' + data.evidenceModel.localName)
		};
		modalStore.trigger(modal);
	}

	let refreshKey = false;
	function forceRefresh() {
		refreshKey = !refreshKey;
	}

	let resetForm = true;

	$: formStore = _form.form;

	$: if (form?.newEvidence) {
		refreshKey = !refreshKey;
		resetForm = false;
		_form.form.update(
			(current: Record<string, any>) => ({
				...current,
				evidences: current.evidences
					? [...current.evidences, form?.newEvidence]
					: [form?.newEvidence]
			}),
			{ taint: false }
		);
		console.debug('formStore', $formStore);
	}

	const user = $page.data.user;
	const canEditObject: boolean = canPerformAction({
		user,
		action: 'change',
		model: data.model.name,
		domain:
			data.model.name === 'folder'
				? data.data.id
				: (data.data.folder?.id ?? data.data.folder ?? user.root_folder_id)
	});
</script>

<div class="flex flex-col space-y-2">
	<DetailView {data} displayModelTable={false}>
		<div
			slot="widgets"
			class="shadow-xl border-l border-t p-4 rounded bg-gradient-to-tl from-slate-50 to-white"
			hidden={!canEditObject}
		>
			{#if canEditObject}
				<!-- new record form -->
				<h1 class="text-xl font-bold font-serif mb-2">{m.addTimelineEntry()}</h1>
				<SuperForm
					class="flex flex-col space-y-3"
					action={formAction}
					dataType={'json'}
					enctype={'application/x-www-form-urlencoded'}
					data={timelineForm}
					{_form}
					{invalidateAll}
					let:form
					let:data
					let:initialData
					validators={zod(schema)}
					{...$$restProps}
				>
					<AutocompleteSelect
						{form}
						optionsEndpoint="incidents"
						field="incident"
						label={m.incident()}
						hidden={initialData.incident}
					/>
					<Select
						{form}
						disableDoubleDash={true}
						options={model.selectOptions['entry_type']}
						field="entry_type"
						label={m.entryType()}
					/>
					{#key refreshKey}
						<TextField
							type="datetime-local"
							step="1"
							{form}
							field="timestamp"
							label={m.timestamp()}
						/>
					{/key}
					<TextField {form} field="entry" label={m.entry()} data-focusindex="0" />
					<TextArea {form} field="observation" label={m.observation()} />
					{#key refreshKey}
						<div class="flex items-end justify-center">
							<div class="w-full mr-2">
								<AutocompleteSelect
									{form}
									multiple
									optionsEndpoint="evidences"
									field="evidences"
									{resetForm}
									label={m.evidences()}
								/>
							</div>
							<button
								class="btn bg-gray-300 h-11 w-10"
								on:click={(_) => modalEvidenceCreateForm()}
								type="button"><i class="fa-solid fa-plus text-sm" /></button
							>
						</div>
					{/key}
					<div class="flex flex-row justify-between space-x-4">
						<button
							class="btn variant-filled-tertiary font-semibold w-full"
							data-testid="reset-button"
							type="button"
							on:click={() => {
								_form.reset();
								_form.form.update((current) => ({
									...current,
									evidences: undefined,
									timestamp: new Date().toISOString()
								}));
								refreshKey = !refreshKey;
								resetForm = true;
							}}>{m.cancel()}</button
						>
						<button
							class="btn variant-filled-primary font-semibold w-full"
							data-testid="save-button"
							type="submit"
							on:click={() => {
								resetForm = true;
							}}>{m.save()}</button
						>
					</div>
				</SuperForm>
			{/if}
		</div>
	</DetailView>

	<div class="card shadow-lg bg-white p-4 space-y-2">
		<div class="flex flex-row justify-between items-center">
			<h1 class="text-xl font-bold font-serif">{m.timeline()}</h1>
			<Search {handler} />
			<RowsPerPage {handler} />
		</div>
		<ol class="relative border-s border-primary-500 dark:border-primary-700">
			{#each $rows as row, rowIndex}
				{@const meta = row?.meta ?? row}
				{@const actionsURLModel = 'timeline-entries'}
				<li class="mb-10 ms-4">
					<div
						class="absolute w-3 h-3 bg-primary-500 rounded-full mt-1.5 -start-1.5 border border-white dark:border-primary-900 dark:bg-primary-700"
					></div>
					<div class="flex flex-col">
						<div class="flex flex-row items-center space-x-3">
							<time class="mb-1 text-sm font-normal leading-none text-gray-400 dark:text-gray-500">
								{formatDateOrDateTime(meta.timestamp, getLocale())} - {#if meta.author}{meta?.author
										?.str}{:else}{m.unknownOrDeletedUser()}{/if}</time
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
						<div class="mb-1">
							<span class="text-xs font-mono bg-violet-700 text-white p-1 rounded"
								>{safeTranslate(meta.entry_type)}</span
							>
						</div>
						<a href={`/${actionsURLModel}/${meta.id}`} class="font-semibold capitalize"
							>{safeTranslate(meta.entry)}</a
						>
						<p class="text-xs italic text-gray-500 dark:text-gray-400 whitespace-pre-line">
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
