<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '../Select.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import { defaults, type SuperForm, type SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { getModelInfo } from '$lib/utils/crud';
	import { formatSelectFieldData } from '$lib/utils/load';
	import { safeTranslate } from '$lib/utils/i18n';
	import { AppliedControlSchema, TaskTemplateSchema } from '$lib/utils/schemas';
	import { zod4 as zod } from 'sveltekit-superforms/adapters';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { invalidateAll } from '$app/navigation';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import {
		getModalStore,
		type ModalComponent,
		type ModalSettings
	} from '$lib/components/Modals/stores';

	interface Props {
		form: SuperForm<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		context?: string;
		object?: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		context = 'default',
		object
	}: Props = $props();

	let isParentLocked = $derived(object?.findings_assessment?.is_locked || false);

	const formData = form.form;

	// `initialData` is the superform's own data, so on edit it carries the persisted
	// parent too: only a create context preseting it means "don't offer the choice".
	let presetBinder = $derived(context === 'create' && !!initialData.findings_assessment);

	// The folder of a finding attached to a binder is the binder's own: mirror the
	// server-side rule here so the picker never shows a value that would be rejected.
	let boundToBinder = $derived(!!$formData?.findings_assessment);
	let folderKey = $state(0);

	async function handleBinderChange(binderId: string | null | undefined) {
		if (!binderId) return;
		const res = await fetch(`/findings-assessments/${binderId}`);
		if (!res.ok) return;
		const binder = await res.json();
		// A slower earlier response must not drag the folder back to a stale binder.
		if (binderId !== $formData.findings_assessment) return;
		if (!binder.folder?.id || binder.folder.id === $formData.folder) return;
		form.form.update((current) => ({ ...current, folder: binder.folder.id }), {
			taint: false
		});
		folderKey++;
	}

	const modalStore = getModalStore();

	const appliedControlModel = getModelInfo('applied-controls');
	const taskTemplateModel = getModelInfo('task-templates');

	// Populated on mount rather than by a server load, so every `selectOptions` read
	// below has to tolerate the first render.
	//
	// Driven by the model's own `selectFields` and passed through the same formatter the
	// server load uses: severity and priority are `valueType: 'number'`, and fetching the
	// endpoints raw would hand the form strings the schema rejects.
	onMount(async () => {
		if (model.selectOptions) return;
		const entries = await Promise.all(
			(model.selectFields ?? []).map(async (selectField) => {
				const res = await fetch(`/${model.urlModel}/${selectField.field}`);
				if (!res.ok) return [selectField.field, []];
				return [selectField.field, formatSelectFieldData(await res.json(), selectField)];
			})
		);
		model.selectOptions = Object.fromEntries(entries);
	});

	// Both remediation vehicles are creatable from the finding, pre-linked to it.
	function modalRemediationCreateForm(remediationModel: ModelInfo, schema: any): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: defaults({ findings: [page.data.object.id] }, zod(schema)),
				formAction: `/${remediationModel.urlModel}?/create`,
				model: remediationModel,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			title: safeTranslate('add-' + remediationModel.localName),
			response: (r: boolean) => {
				if (r) {
					invalidateAll();
				}
			}
		};
		modalStore.trigger(modal);
	}
</script>

<AutocompleteSelect
	{form}
	nullable
	optionsEndpoint="findings-assessments"
	optionsExtraFields={[['folder', 'str']]}
	field="findings_assessment"
	cacheLock={cacheLocks['findings_assessment']}
	bind:cachedValue={formDataCache['findings_assessment']}
	label={m.findingsAssessment()}
	helpText={m.findingsAssessmentHelpText()}
	hidden={presetBinder}
	onChange={handleBinderChange}
/>
{#key folderKey}
	<FolderTreeSelect
		{form}
		field="folder"
		cacheLock={cacheLocks['folder']}
		bind:cachedValue={formDataCache['folder']}
		label={m.domain()}
		required={!boundToBinder}
		disabled={boundToBinder}
		hidden={presetBinder}
		helpText={boundToBinder ? m.findingFolderFromBinderHelpText() : undefined}
	/>
{/key}
<Select
	{form}
	options={model.selectOptions?.['severity'] ?? []}
	field="severity"
	label={m.severity()}
	cacheLock={cacheLocks['severity']}
	bind:cachedValue={formDataCache['severity']}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="actors"
	optionsLabelField="str"
	optionsInfoFields={{
		fields: [{ field: 'type', translate: true }],
		position: 'prefix'
	}}
	field="owner"
	cacheLock={cacheLocks['owner']}
	bind:cachedValue={formDataCache['owner']}
	label={m.owner()}
/>
<Select
	{form}
	options={model.selectOptions?.['status'] ?? []}
	field="status"
	label={m.status()}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/>
<TextField
	type="date"
	{form}
	field="eta"
	label={m.eta()}
	helpText={m.etaHelpText()}
	cacheLock={cacheLocks['eta']}
	bind:cachedValue={formDataCache['eta']}
/>
<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<Select
		{form}
		options={model.selectOptions?.['priority'] ?? []}
		field="priority"
		label={m.priority()}
		cacheLock={cacheLocks['priority']}
		bind:cachedValue={formDataCache['priority']}
	/>
	<div class="flex flex-row space-x-2 items-center">
		<div class="w-full">
			{#key page.data}
				<AutocompleteSelect
					multiple
					lazy
					{form}
					optionsEndpoint="applied-controls"
					optionsExtraFields={[['folder', 'str']]}
					optionsInfoFields={{
						fields: [{ field: 'category', translate: true }],
						position: 'prefix'
					}}
					field="applied_controls"
					label={m.appliedControls()}
				/>
			{/key}
		</div>
		{#if context !== 'create'}
			<div class="mt-4">
				<button
					class="btn bg-surface-300-700 h-10 w-10"
					aria-label={m.addAppliedControl()}
					onclick={(_) => modalRemediationCreateForm(appliedControlModel, AppliedControlSchema)}
					type="button"><i class="fa-solid fa-plus text-sm"></i></button
				>
			</div>
		{/if}
	</div>
	<div class="flex flex-row space-x-2 items-center">
		<div class="w-full">
			<AutocompleteSelect
				multiple
				lazy
				{form}
				optionsEndpoint="task-templates"
				optionsLabelField="auto"
				optionsExtraFields={[['folder', 'str']]}
				field="task_templates"
				cacheLock={cacheLocks['task_templates']}
				bind:cachedValue={formDataCache['task_templates']}
				label={m.taskTemplates()}
			/>
		</div>
		{#if context !== 'create'}
			<div class="mt-4">
				<button
					class="btn bg-surface-300-700 h-10 w-10"
					aria-label={m.addTaskTemplate()}
					onclick={(_) => modalRemediationCreateForm(taskTemplateModel, TaskTemplateSchema)}
					type="button"><i class="fa-solid fa-plus text-sm"></i></button
				>
			</div>
		{/if}
	</div>
	<AutocompleteSelect
		{form}
		lazy
		optionsEndpoint="assets"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="asset"
		cacheLock={cacheLocks['asset']}
		bind:cachedValue={formDataCache['asset']}
		label={m.asset()}
	/>
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="threats"
		field="threats"
		label={m.threats()}
	/>
	<AutocompleteSelect
		multiple
		lazy
		{form}
		optionsEndpoint="vulnerabilities"
		optionsExtraFields={[['folder', 'str']]}
		field="vulnerabilities"
		label={m.vulnerabilities()}
	/>
	<AutocompleteSelect
		multiple
		{form}
		optionsEndpoint="evidences"
		optionsExtraFields={[['folder', 'str']]}
		optionsLabelField="auto"
		field="evidences"
		label={m.evidences()}
		cacheLock={cacheLocks['evidences']}
		bind:cachedValue={formDataCache['evidences']}
	/>
	<TextField
		type="date"
		{form}
		field="due_date"
		label={m.dueDate()}
		helpText={m.dueDateHelpText()}
		cacheLock={cacheLocks['due_date']}
		bind:cachedValue={formDataCache['due_date']}
	/>
	<MarkdownField
		{form}
		field="recommendation"
		label={m.recommendation()}
		helpText={m.recommendationHelpText()}
		cacheLock={cacheLocks['recommendation']}
		bind:cachedValue={formDataCache['recommendation']}
	/>
	<MarkdownField
		{form}
		field="observation"
		label={m.observation()}
		helpText={m.observationHelpText()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
	<AutocompleteSelect
		multiple
		{form}
		createFromSelection={true}
		optionsEndpoint="filtering-labels"
		optionsLabelField="label"
		translateOptions={false}
		field="filtering_labels"
		helpText={m.labelsHelpText()}
		label={m.labels()}
		allowUserOptions="append"
	/>
</Dropdown>
