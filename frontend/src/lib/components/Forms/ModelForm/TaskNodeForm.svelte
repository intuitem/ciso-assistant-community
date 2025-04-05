<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '../TextField.svelte';
	import TextArea from '../TextArea.svelte';
	import Select from '../Select.svelte';
	import Checkbox from '../Checkbox.svelte';
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
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
<Select
	{form}
	field="status"
	disableDoubleDash={true}
	options={model.selectOptions['status']}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
	label={m.status()}
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
	field="due_date"
	label={m.dueDate()}
	helpText={m.dueDateHelpText()}
	cacheLock={cacheLocks['due_date']}
	bind:cachedValue={formDataCache['due_date']}
/>
<TextField
	type="date"
	{form}
	field="completion_date"
	label={m.completionDate()}
	helpText={m.completionDateHelpText()}
	cacheLock={cacheLocks['completion_date']}
	bind:cachedValue={formDataCache['completion_date']}
/>
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="assets"
	optionsExtraFields={[['folder', 'str']]}
	optionsLabelField="auto"
	field="assets"
	label={m.assets()}
/>
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="applied-controls"
	optionsExtraFields={[['folder', 'str']]}
	field="applied_controls"
	label={m.appliedControls()}
/>
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="compliance-assessments"
	field="compliance_assessments"
	cacheLock={cacheLocks['compliance_assessments']}
	bind:cachedValue={formDataCache['compliance_assessments']}
	label={m.complianceAssessments()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="risk-assessments"
	optionsExtraFields={[['perimeter', 'str']]}
	optionsLabelField="str"
	field="risk_assessment"
	cacheLock={cacheLocks['risk_assessment']}
	bind:cachedValue={formDataCache['risk_assessment']}
	label={m.riskAssessments()}
/>
<TextArea
	{form}
	field="observation"
	label={m.observation()}
	cacheLock={cacheLocks['observation']}
	bind:cachedValue={formDataCache['observation']}
/>
<Checkbox {form} field="is_template" label={m.isRecurrent()} helpText={m.isRecurrentHelpText()} />
<Checkbox {form} field="enabled" label={m.enabled()}/>
