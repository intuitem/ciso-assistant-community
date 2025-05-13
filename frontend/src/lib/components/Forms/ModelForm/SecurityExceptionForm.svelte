<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import HiddenInput from '../HiddenInput.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '../Select.svelte';
	import { defaults, type SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import { getModalStore, type ModalComponent, type ModalSettings } from '@skeletonlabs/skeleton';
	import { onMount } from 'svelte';
	import { getModelInfo } from '$lib/utils/crud';
	import { zod } from 'sveltekit-superforms/adapters';
	import { safeTranslate } from '$lib/utils/i18n';
	import { invalidateAll } from '$app/navigation';
	import { AppliedControlSchema } from '$lib/utils/schemas';
	import { page } from '$app/stores';
	import CreateModal from '$lib/components/Modals/CreateModal.svelte';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		context?: string;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		context = 'default'
	}: Props = $props();

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
						security_exceptions: [$page.data.object.id]
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

<HiddenInput {form} field="requirement_assessments" />
<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="users?is_third_party=false"
	optionsLabelField="email"
	field="owners"
	cacheLock={cacheLocks['owners']}
	bind:cachedValue={formDataCache['owners']}
	label={m.owners()}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="users?is_approver=true"
	optionsLabelField="email"
	field="approver"
	cacheLock={cacheLocks['approver']}
	bind:cachedValue={formDataCache['approver']}
	nullable={true}
	label={m.approver()}
	helpText={m.approverHelpText()}
/>
<Select
	{form}
	options={model.selectOptions['severity']}
	field="severity"
	label={m.severity()}
	cacheLock={cacheLocks['severity']}
	bind:cachedValue={formDataCache['severity']}
/>
<Select
	{form}
	options={model.selectOptions['status']}
	field="status"
	label={m.status()}
	cacheLock={cacheLocks['status']}
	disableDoubleDash="true"
	bind:cachedValue={formDataCache['status']}
/>
<TextField
	type="date"
	{form}
	field="expiration_date"
	label={m.expirationDate()}
	cacheLock={cacheLocks['expiration_date']}
	bind:cachedValue={formDataCache['expiration_date']}
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
				onclick={(_) => modalAppliedControlCreateForm('applied_controls')}
				type="button"><i class="fa-solid fa-plus text-sm"></i></button
			>
		</div>
	{/if}
</div>
