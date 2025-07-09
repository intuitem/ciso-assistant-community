<script lang="ts">
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
		context?: {
			selectElementaryActions?: boolean;
		};
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		context = {}
	}: Props = $props();
</script>

{#if context !== 'selectElementaryActions'}
	<TextField
		{form}
		field="name"
		label={m.name()}
		cacheLock={cacheLocks['name']}
		bind:cachedValue={formDataCache['name']}
	/>
	<AutocompleteSelect
		{form}
		optionsEndpoint="operational-scenarios"
		field="operational_scenario"
		cacheLock={cacheLocks['operational_scenario']}
		bind:cachedValue={formDataCache['operational_scenario']}
		label={m.operationalScenario()}
		hidden
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
		options={model.selectOptions['likelihood']}
		field="likelihood"
		label={m.likelihood()}
		cacheLock={cacheLocks['likelihood']}
		bind:cachedValue={formDataCache['likelihood']}
		helpText={m.likelihoodHelpText()}
	/>
{/if}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="elementary-actions"
		field="elementary_actions"
		cacheLock={cacheLocks['elementary_actions']}
		bind:cachedValue={formDataCache['elementary_actions']}
		label={m.elementaryActions()}
	/>
