<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '#lib/components/Forms/TextField.svelte';
	import MarkdownField from '#lib/components/Forms/MarkdownField.svelte';
	import Select from '../Select.svelte';
	import Checkbox from '../Checkbox.svelte';
	import Dropdown from '#lib/components/Dropdown/Dropdown.svelte';
	import type { SuperForm } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '#lib/utils/types.js';
	import * as m from '#paraglide/messages.js';
	import { SENSITIVE_PERSONAL_DATA_CATEGORIES } from '#lib/utils/constants.js';

	interface Props {
		form: SuperForm<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {}
	}: Props = $props();

	const formData = form.form;
	// Derived so the effect below only reruns when the category changes, not on every field edit
	const categoryId = $derived($formData.category);
	let categoryIsSensitive = $state(false);
	// The user's own value, set aside while a sensitive category locks the checkbox
	let valueBeforeLock: boolean | null = null;
	// On edit, a stored true under a sensitive category was forced by the backend, not chosen
	let firstResolution = true;

	function setSensitive(value: boolean) {
		form.form.update((current) => ({ ...current, is_sensitive: value }));
	}

	function applyLock(sensitive: boolean) {
		categoryIsSensitive = sensitive;
		if (sensitive && valueBeforeLock === null) {
			valueBeforeLock = firstResolution ? false : !!$formData.is_sensitive;
			setSensitive(true);
		} else if (!sensitive && valueBeforeLock !== null) {
			setSensitive(valueBeforeLock);
			valueBeforeLock = null;
		}
		firstResolution = false;
	}

	// Art. 9/10 categories are always sensitive: tick and lock the checkbox, on create and edit
	$effect(() => {
		const id = categoryId;
		if (!id) {
			applyLock(false);
			return;
		}
		fetch(`/terminologies/${id}`)
			.then((res) => (res.ok ? res.json() : null))
			.then((term) => {
				if (!term || $formData.category !== id) return;
				applyLock(SENSITIVE_PERSONAL_DATA_CATEGORIES.has(term.name));
			});
	});
</script>

<AutocompleteSelect
	{form}
	field="category"
	optionsEndpoint="terminologies?field_path=personal_data.category&is_visible=true"
	optionsLabelField="translated_name"
	cacheLock={cacheLocks['category']}
	bind:cachedValue={formDataCache['category']}
	label={m.category()}
/>

<TextField
	{form}
	field="retention"
	label={m.retention()}
	cacheLock={cacheLocks['retention']}
	bind:cachedValue={formDataCache['retention']}
/>
<AutocompleteSelect
	{form}
	field="deletion_policy"
	options={model.selectOptions['deletion_policy']}
	cacheLock={cacheLocks['deletion_policy']}
	bind:cachedValue={formDataCache['deletion_policy']}
	label={m.deletionPolicy()}
/>
<AutocompleteSelect
	{form}
	field="processing"
	optionsEndpoint="processings"
	cacheLock={cacheLocks['processing']}
	bind:cachedValue={formDataCache['processing']}
	label={m.processing()}
	hidden={initialData.processing}
/>

<Checkbox
	{form}
	field="is_sensitive"
	label={m.isSensitive()}
	disabled={categoryIsSensitive}
	helpText={categoryIsSensitive ? m.sensitiveCategoryHelpText() : undefined}
	cacheLock={cacheLocks['is_sensitive']}
	bind:cachedValue={formDataCache['is_sensitive']}
/>

<AutocompleteSelect
	{form}
	lazy
	field="assets"
	optionsEndpoint="assets"
	optionsLabelField="auto"
	optionsExtraFields={[['folder', 'str']]}
	optionsInfoFields={{
		fields: [
			{
				field: 'type',
				translate: true
			}
		],
		classes: 'text-blue-500'
	}}
	cacheLock={cacheLocks['assets']}
	bind:cachedValue={formDataCache['assets']}
	label={m.assets()}
	multiple={true}
/>

<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<TextField
		{form}
		field="name"
		label={m.name()}
		cacheLock={cacheLocks['name']}
		bind:cachedValue={formDataCache['name']}
	/>
	<MarkdownField
		{form}
		field="description"
		label={m.description()}
		cacheLock={cacheLocks['description']}
		bind:cachedValue={formDataCache['description']}
	/>
</Dropdown>
