<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import FolderTreeSelect from '../FolderTreeSelect.svelte';
	import Select from '../Select.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import NumberField from '../NumberField.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
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
</script>

<FolderTreeSelect
	{form}
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
/>
<Select
	{form}
	options={[
		{ label: 'CVE', value: 'CVE' },
		{ label: 'EUVD', value: 'EUVD' },
		{ label: 'GHSA', value: 'GHSA' },
		{ label: 'Other', value: 'other' }
	]}
	field="source"
	label={m.source()}
	cacheLock={cacheLocks['source']}
	bind:cachedValue={formDataCache['source']}
/>
<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>
<TextField
	type="date"
	{form}
	field="published_date"
	label={m.publishedDate()}
	cacheLock={cacheLocks['published_date']}
	bind:cachedValue={formDataCache['published_date']}
/>
<NumberField {form} field="cvss_base_score" label={m.cvssBaseScore()} min={0} max={10} step={0.1} />
<TextField
	{form}
	field="cvss_vector"
	label={m.cvssVector()}
	cacheLock={cacheLocks['cvss_vector']}
	bind:cachedValue={formDataCache['cvss_vector']}
/>
<TextArea
	{form}
	field="annotation"
	label={m.annotation()}
	cacheLock={cacheLocks['annotation']}
	bind:cachedValue={formDataCache['annotation']}
/>
<TextField
	{form}
	field="provider"
	label={m.provider()}
	cacheLock={cacheLocks['provider']}
	bind:cachedValue={formDataCache['provider']}
/>
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
