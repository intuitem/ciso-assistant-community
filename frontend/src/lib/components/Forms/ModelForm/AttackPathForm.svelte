<script lang="ts">
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import { m } from '$paraglide/messages';
	import type { SuperValidated } from 'sveltekit-superforms';
	import Checkbox from '../Checkbox.svelte';
	import TextArea from '../TextArea.svelte';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		additionalInitialData?: Record<string, any>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		additionalInitialData = {}
	}: Props = $props();
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="strategic-scenarios"
	optionsDetailedUrlParameters={[['ebios_rm_study', additionalInitialData.ebios_rm_study]]}
	field="strategic_scenario"
	cacheLock={cacheLocks['strategic_scenario']}
	bind:cachedValue={formDataCache['strategic_scenario']}
	label={m.strategicScenario()}
	hidden={initialData['strategic_scenario']}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="stakeholders"
	optionsDetailedUrlParameters={[['ebios_rm_study', additionalInitialData.ebios_rm_study]]}
	optionsLabelField="str"
	field="stakeholders"
	cacheLock={cacheLocks['stakeholders']}
	bind:cachedValue={formDataCache['stakeholders']}
	label={m.stakeholders()}
	helpText={m.attackPathStakeholdersHelpText()}
/>

<Checkbox
	{form}
	field="is_selected"
	label={m.selected()}
	helpText={m.attackPathIsSelectedHelpText()}
/>
<TextArea
	{form}
	field="justification"
	label={m.justification()}
	cacheLock={cacheLocks['justification']}
	bind:cachedValue={formDataCache['justification']}
/>
