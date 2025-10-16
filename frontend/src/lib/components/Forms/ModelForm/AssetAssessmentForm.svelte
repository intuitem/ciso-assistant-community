<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Checkbox from '../Checkbox.svelte';
	import Select from '../Select.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		duplicate?: boolean;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: Record<string, any>; // export let context: string = 'default';
	}

	let {
		form,
		model,
		duplicate = false,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {}
	}: Props = $props();

	// export let updated_fields: Set<string> = new Set();
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="assets"
	optionsExtraFields={[['folder', 'str']]}
	optionsInfoFields={{
		fields: [
			{
				field: 'type'
			}
		],
		classes: 'text-blue-500'
	}}
	field="asset"
	cacheLock={cacheLocks['asset']}
	bind:cachedValue={formDataCache['asset']}
	label={m.asset()}
	hidden={initialData.asset}
	helpText={m.scopedAsset()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="assets"
	optionsExtraFields={[['folder', 'str']]}
	optionsInfoFields={{
		fields: [
			{
				field: 'type'
			}
		],
		classes: 'text-blue-500'
	}}
	field="dependencies"
	cacheLock={cacheLocks['dependencies']}
	bind:cachedValue={formDataCache['dependencies']}
	label={m.extraDependencies()}
	helpText={m.extraDependenciesHelpText()}
/>
<AutocompleteSelect
	{form}
	field="bia"
	optionsEndpoint="business-impact-analysis"
	cacheLock={cacheLocks['bia']}
	bind:cachedValue={formDataCache['bia']}
	label={m.bia()}
	hidden={initialData.bia}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="applied-controls"
	optionsExtraFields={[['folder', 'str']]}
	field="associated_controls"
	cacheLock={cacheLocks['associated_controls']}
	bind:cachedValue={formDataCache['associated_controls']}
	label={m.associatedControls()}
	helpText={m.associatedControlsBiaHelpText()}
/>
<Checkbox {form} field="recovery_documented" label={m.recoveryDocumented()} />
<Checkbox {form} field="recovery_tested" label={m.recoveryTested()} />
<Checkbox {form} field="recovery_targets_met" label={m.recoveryTargetsMet()} />
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="evidences"
	optionsExtraFields={[['folder', 'str']]}
	field="evidences"
	cacheLock={cacheLocks['evidences']}
	bind:cachedValue={formDataCache['evidences']}
	label={m.evidences()}
	helpText={m.evidencesBiaHelpText()}
/>
<MarkdownField
	{form}
	field="observation"
	label={m.observation()}
	cacheLock={cacheLocks['observation']}
	bind:cachedValue={formDataCache['observation']}
/>
