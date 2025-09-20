<script lang="ts">
	import HiddenInput from '../HiddenInput.svelte';
	import FileInput from '../FileInput.svelte';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		context: string;
		object?: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {},
		context
	}: Props = $props();

	function getFilename(path) {
		if (!path) return '';

		try {
			// If it's a URL with query parameters
			const withoutQuery = path.split('?')[0];
			// Get the last part after the final slash (if any)
			return decodeURIComponent(withoutQuery.split('/').pop());
		} catch (e) {
			return path; // Fallback to original string if anything fails
		}
	}
</script>

<HiddenInput {form} field="applied_controls" />
<HiddenInput {form} field="requirement_assessments" />
<HiddenInput {form} field="findings" />
<HiddenInput {form} field="findings_assessments" />
<HiddenInput {form} field="timeline_entries" />

{#if context !== 'edit'}
	<FileInput
		{form}
		allowPaste={true}
		helpText={object.attachment
			? `${m.attachmentWarningText()}: ${getFilename(object.attachment)}`
			: m.attachmentHelpText()}
		field="attachment"
		label={m.attachment()}
		allowedExtensions={'*'}
	/>
{/if}
{#if !(initialData.applied_controls || initialData.requirement_assessments)}
	<AutocompleteSelect
		{form}
		optionsEndpoint="folders"
		field="folder"
		pathField="path"
		cacheLock={cacheLocks['folder']}
		bind:cachedValue={formDataCache['folder']}
		label={m.domain()}
		hidden={initialData.applied_controls ||
			initialData.requirement_assessments ||
			initialData.folder}
	/>
{:else}
	<HiddenInput {form} field="folder" />
{/if}
{#if context !== 'edit'}
	<TextField
		{form}
		field="link"
		label={m.link()}
		helpText={m.linkHelpText()}
		cacheLock={cacheLocks['link']}
		bind:cachedValue={formDataCache['link']}
	/>
{/if}
<AutocompleteSelect
	multiple
	{form}
	createFromSelection={true}
	optionsEndpoint="filtering-labels"
	optionsLabelField="label"
	field="filtering_labels"
	translateOptions={false}
	helpText={m.labelsHelpText()}
	label={m.labels()}
	allowUserOptions="append"
/>

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
	disableDoubleDash={true}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
/>

<TextField
	type="date"
	{form}
	field="expiry_date"
	label={m.expiryDate()}
	cacheLock={cacheLocks['expiry_date']}
	bind:cachedValue={formDataCache['expiry_date']}
/>
