<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import Checkbox from '../Checkbox.svelte';
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

{#if !initialData['operating_mode']}
	<AutocompleteSelect
		{form}
		optionsEndpoint="operating-modes"
		field="operating_mode"
		cacheLock={cacheLocks['operating_mode']}
		bind:cachedValue={formDataCache['operating_mode']}
		label={m.operatingMode()}
		hidden
	/>
{/if}
<AutocompleteSelect
	{form}
	optionsEndpoint="elementary-actions"
	optionsDetailedUrlParameters={[['operating_mode_available_actions', initialData['operating_mode']]]}
	field="elementary_action"
	cacheLock={cacheLocks['elementary_action']}
	bind:cachedValue={formDataCache['elementary_action']}
	label={m.elementaryAction()}
	hidden={initialData.elementary_action}
/>
<Checkbox
	{form}
	field="is_highlighted"
	label={m.isHighlighted()}
	cacheLock={cacheLocks['is_highlighted']}
	bind:cachedValue={formDataCache['is_highlighted']}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="elementary-actions"
	optionsDetailedUrlParameters={[['operating_modes', initialData['operating_mode']]]}
	multiple
	field="antecedents"
	cacheLock={cacheLocks['antecedents']}
	helpText={m.antecedentsHelpText()}
	bind:cachedValue={formDataCache['antecedents']}
	label={m.antecedents()}
/>
<Select
	{form}
	options={model.selectOptions['logic_operator']}
	field="logic_operator"
	label={m.logicOperator()}
	helpText={m.logicOperatorHelpText()}
	cacheLock={cacheLocks['logic_operator']}
	bind:cachedValue={formDataCache['logic_operator']}
	disabled={formDataCache['antecedents'] && formDataCache['antecedents'].length <= 1}
/>
