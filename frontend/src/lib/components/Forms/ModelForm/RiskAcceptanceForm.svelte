<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import { getOptions } from '$lib/utils/crud';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { page } from '$app/stores';
	import * as m from '$paraglide/messages.js';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let object: Record<string, any> = {};
	export let initialData: Record<string, any> = {};
</script>

<TextField
	{form}
	type="date"
	field="expiry_date"
	label={m.expiryDate()}
	helpText={m.expiryDateHelpText()}
	cacheLock={cacheLocks['expiry_date']}
	bind:cachedValue={formDataCache['expiry_date']}
/>
{#if object.id && $page.data.user.id === object.approver}
	<TextArea
		disabled={$page.data.user.id !== object.approver}
		{form}
		field="justification"
		label={m.justification()}
		helpText={m.riskAcceptanceJusitficationHelpText()}
		cacheLock={cacheLocks['justification']}
		bind:cachedValue={formDataCache['justification']}
	/>
{/if}
<AutocompleteSelect
	{form}
	options={getOptions({ objects: model.foreignKeys['folder'] })}
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
<AutocompleteSelect
	{form}
	options={getOptions({ objects: model.foreignKeys['approver'], label: 'email' })}
	field="approver"
	cacheLock={cacheLocks['approver']}
	bind:cachedValue={formDataCache['approver']}
	label={m.approver()}
	helpText={m.approverHelpText()}
/>
<AutocompleteSelect
	{form}
	options={getOptions({
		objects: model.foreignKeys['risk_scenarios'],
		extra_fields: [
			['project', 'str'],
			['risk_assessment', 'str']
		]
	})}
	field="risk_scenarios"
	cacheLock={cacheLocks['risk_scenarios']}
	bind:cachedValue={formDataCache['risk_scenarios']}
	label={m.riskScenarios()}
	helpText={m.riskAcceptanceRiskScenariosHelpText()}
	multiple
/>
