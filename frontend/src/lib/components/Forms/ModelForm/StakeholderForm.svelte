<script lang="ts">
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import * as m from '$paraglide/messages.js';
	import { getOptions } from '$lib/utils/crud';
	import TextArea from '../TextArea.svelte';
	import NumberField from '../NumberField.svelte';
	import Checkbox from '../Checkbox.svelte';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
	export let context: 'create' | 'edit' = 'create';
</script>

<AutocompleteSelect
	{form}
	options={getOptions({ objects: model.foreignKeys['entity'] })}
	field="entity"
	cacheLock={cacheLocks['entity']}
	bind:cachedValue={formDataCache['entity']}
	label={m.entity()}
	hidden={initialData.entity}
/>
<Select
	{form}
	options={model.selectOptions['category']}
	field="category"
	label={m.category()}
	cacheLock={cacheLocks['category']}
	bind:cachedValue={formDataCache['category']}
/>

{#if context === 'edit'}
	<NumberField
		{form}
		field="current_dependency"
		label={m.currentDependency()}
		cacheLock={cacheLocks['current_dependency']}
		bind:cachedValue={formDataCache['current_dependency']}
	/>
	<NumberField
		{form}
		field="current_penetration"
		label={m.currentPenetration()}
		cacheLock={cacheLocks['current_penetration']}
		bind:cachedValue={formDataCache['current_penetration']}
	/>
	<NumberField
		{form}
		field="current_maturity"
		label={m.currentMaturity()}
		cacheLock={cacheLocks['current_maturity']}
		bind:cachedValue={formDataCache['current_maturity']}
	/>
	<NumberField
		{form}
		field="current_trust"
		label={m.currentTrust()}
		cacheLock={cacheLocks['current_trust']}
		bind:cachedValue={formDataCache['current_trust']}
	/>

	<AutocompleteSelect
		multiple
		{form}
		options={getOptions({
			objects: model.foreignKeys['applied_controls'],
			extra_fields: [['folder', 'str']]
		})}
		field="applied_controls"
		label={m.appliedControls()}
	/>

	<NumberField
		{form}
		field="residual_dependency"
		label={m.residualDependency()}
		cacheLock={cacheLocks['residual_dependency']}
		bind:cachedValue={formDataCache['residual_dependency']}
	/>
	<NumberField
		{form}
		field="residual_penetration"
		label={m.residualPenetration()}
		cacheLock={cacheLocks['residual_penetration']}
		bind:cachedValue={formDataCache['residual_penetration']}
	/>
	<NumberField
		{form}
		field="residual_maturity"
		label={m.residualMaturity()}
		cacheLock={cacheLocks['residual_maturity']}
		bind:cachedValue={formDataCache['residual_maturity']}
	/>
	<NumberField
		{form}
		field="residual_trust"
		label={m.residualTrust()}
		cacheLock={cacheLocks['residual_trust']}
		bind:cachedValue={formDataCache['residual_trust']}
	/>

	<Checkbox {form} field="is_selected" label={m.selected()} />
	<TextArea
		{form}
		field="justification"
		label={m.justification()}
		cacheLock={cacheLocks['justification']}
		bind:cachedValue={formDataCache['justification']}
	/>
{/if}
