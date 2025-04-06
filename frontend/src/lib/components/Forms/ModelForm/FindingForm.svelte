<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '../Select.svelte';
	import { defaults, type SuperForm, type SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalComponent, type ModalSettings } from '@skeletonlabs/skeleton';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';
	import { getModelInfo } from '$lib/utils/crud';
	import { safeTranslate } from '$lib/utils/i18n';
	import { AppliedControlSchema } from '$lib/utils/schemas';
	import { zod } from 'sveltekit-superforms/adapters';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { invalidateAll } from '$app/navigation';

	export let form: SuperForm<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let context = 'default';

	const modalStore = getModalStore();

	let appliedControlModel: ModelInfo;
	onMount(async () => {
		appliedControlModel = getModelInfo('applied-controls');
		const selectOptions = {
			status: await fetch('/applied-controls/status').then((r) => r.json()),
			priority: await fetch('/applied-controls/priority').then((r) => r.json()),
			category: await fetch('/applied-controls/category').then((r) => r.json()),
			csf_function: await fetch('/applied-controls/csf_function').then((r) => r.json()),
			effort: await fetch('/applied-controls/effort').then((r) => r.json())
		};
		appliedControlModel.selectOptions = selectOptions;
	});

	function modalAppliedControlCreateForm(field: string): void {
		const modalComponent: ModalComponent = {
			ref: CreateModal,
			props: {
				form: defaults(
					{
						findings: [$page.data.object.id]
					},
					zod(AppliedControlSchema)
				),
				formAction: '/applied-controls?/create',
				model: appliedControlModel,
				debug: false
			}
		};
		const modal: ModalSettings = {
			type: 'component',
			component: modalComponent,
			// Data
			title: safeTranslate('add-' + appliedControlModel.localName),
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
	multiple
	optionsEndpoint="users?is_third_party=false"
	optionsLabelField="email"
	field="owner"
	cacheLock={cacheLocks['owner']}
	bind:cachedValue={formDataCache['owner']}
	label={m.owner()}
/>
<Select
	{form}
	options={model.selectOptions['status']}
	field="status"
	label={m.status()}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/>
<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
<Select
	{form}
	options={model.selectOptions['severity']}
	field="severity"
	label={m.severity()}
	cacheLock={cacheLocks['severity']}
	bind:cachedValue={formDataCache['severity']}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="findings-assessments"
	field="findings_assessment"
	cacheLock={cacheLocks['findings_assessment']}
	bind:cachedValue={formDataCache['findings_assessment']}
	label={m.findingsAssessment()}
	hidden={initialData.findings_assessment}
/>
<AutocompleteSelect
	multiple
	{form}
	createFromSelection={true}
	optionsEndpoint="filtering-labels"
	optionsLabelField="label"
	field="filtering_labels"
	helpText={m.labelsHelpText()}
	label={m.labels()}
	allowUserOptions="append"
/>
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="vulnerabilities"
	optionsExtraFields={[['folder', 'str']]}
	field="vulnerabilities"
	label={m.vulnerabilities()}
/>
<div class="flex flex-row space-x-2 items-center">
	<div class="w-full">
		{#key $page.data}
			<AutocompleteSelect
				multiple
				{form}
				optionsEndpoint="applied-controls"
				optionsExtraFields={[['folder', 'str']]}
				field="applied_controls"
				label={m.appliedControls()}
			/>
		{/key}
	</div>
	{#if context !== 'create'}
		<div class="mt-4">
			<button
				class="btn bg-gray-300 h-10 w-10"
				on:click={(_) => modalAppliedControlCreateForm('applied_controls')}
				type="button"><i class="fa-solid fa-plus text-sm" /></button
			>
		</div>
	{/if}
</div>
