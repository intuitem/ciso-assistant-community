<script lang="ts">
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';
	import type { SuperForm } from 'sveltekit-superforms';
	import { formFieldProxy } from 'sveltekit-superforms';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import TextArea from '../TextArea.svelte';
	import TextField from '../TextField.svelte';
	import HiddenInput from '../HiddenInput.svelte';

	interface Props {
		form: SuperForm<any>;
		model: ModelInfo;
		context: string;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
	}

	let {
		form,
		model,
		context,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {}
	}: Props = $props();

	const { value, errors, constraints } = formFieldProxy(form, 'entry_type');

	const formStore = form.form;
</script>

<HiddenInput {form} field="folder" />
{#if context != 'edit'}
	<AutocompleteSelect
		{form}
		optionsEndpoint="incidents"
		field="incident"
		cacheLock={cacheLocks['incident']}
		bind:cachedValue={formDataCache['incident']}
		label={m.incident()}
		hidden={initialData.incident}
	/>
	<Select
		{form}
		options={model.selectOptions['entry_type']}
		field="entry_type"
		label={m.entryType()}
		cacheLock={cacheLocks['entry_type']}
		bind:cachedValue={formDataCache['entry_type']}
	/>
{/if}
{#if !['severity_changed', 'status_changed'].includes($value)}
	<TextField
		{form}
		field="entry"
		label={m.entry()}
		cacheLock={cacheLocks['entry']}
		bind:cachedValue={formDataCache['entry']}
		data-focusindex="0"
	/>
{/if}
<TextField
	type="datetime-local"
	step="1"
	{form}
	field="timestamp"
	label={m.timestamp()}
	cacheLock={cacheLocks['timestamp']}
	bind:cachedValue={formDataCache['timestamp']}
/>
<TextArea
	{form}
	field="observation"
	label={m.observation()}
	cacheLock={cacheLocks['observation']}
	bind:cachedValue={formDataCache['observation']}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="evidences"
	optionsDetailedUrlParameters={$formStore.folder
		? [['scope_folder_id', $formStore.folder]]
		: undefined}
	field="evidences"
	cacheLock={cacheLocks['evidences']}
	bind:cachedValue={formDataCache['evidences']}
	label={m.evidences()}
/>
