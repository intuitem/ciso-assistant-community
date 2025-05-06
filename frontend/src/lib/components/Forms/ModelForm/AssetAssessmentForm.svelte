<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Select from '../Select.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let duplicate: boolean = false;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let object: Record<string, any> = {};
	// export let context: string = 'default';
	// export let updated_fields: Set<string> = new Set();
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="assets"
	field="asset"
	cacheLock={cacheLocks['asset']}
	bind:cachedValue={formDataCache['asset']}
	label={m.asset()}
	hidden={initialData.asset}
	helpText="Scoped asset"
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="assets"
	optionsExtraFields={[['folder', 'str']]}
	field="dependencies"
	cacheLock={cacheLocks['dependencies']}
	bind:cachedValue={formDataCache['dependencies']}
	label={m.dependencies()}
	helpText="Other assets affecting the availability"
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
	helpText="Actions or procedures related to resilience management"
/>
