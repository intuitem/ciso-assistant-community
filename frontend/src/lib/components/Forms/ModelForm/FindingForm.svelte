<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '../Select.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
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
	options={[
		{ label: '--', value: -1 },
		{ label: m.low(), value: 0 },
		{ label: m.medium(), value: 1 },
		{ label: m.high(), value: 2 },
		{ label: m.critical(), value: 3 }
	]}
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
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="applied-controls"
	optionsExtraFields={[['folder', 'str']]}
	field="applied_controls"
	label={m.appliedControls()}
/>
