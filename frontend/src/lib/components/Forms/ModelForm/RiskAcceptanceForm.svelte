<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import { formFieldProxy, type SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { page } from '$app/state';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		object?: Record<string, any>;
		initialData?: Record<string, any>;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		object = {},
		initialData = {}
	}: Props = $props();

	// Live approver value, so "submit for approval" only appears once one is chosen.
	const { value: approverValue } = formFieldProxy(form, 'approver');
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
{#if object.id && page.data.user.id === object.approver}
	<TextArea
		disabled={page.data.user.id !== object.approver}
		{form}
		field="justification"
		label={m.justification()}
		helpText={m.riskAcceptanceJustificationHelpText()}
		cacheLock={cacheLocks['justification']}
		bind:cachedValue={formDataCache['justification']}
	/>
{/if}
<AutocompleteSelect
	{form}
	optionsEndpoint="users?is_approver=true"
	optionsLabelField="email"
	field="approver"
	cacheLock={cacheLocks['approver']}
	bind:cachedValue={formDataCache['approver']}
	nullable={true}
	label={m.approver()}
	helpText={m.approverHelpText()}
/>
{#if !object.id && $approverValue}
	<Checkbox
		{form}
		field="submit"
		label={m.submitForApproval()}
		helpText={m.submitForApprovalHelpText()}
	/>
{/if}
<AutocompleteSelect
	{form}
	optionsEndpoint="risk-scenarios"
	optionsExtraFields={[
		['folder', 'str'],
		['risk_assessment', 'str']
	]}
	field="risk_scenarios"
	cacheLock={cacheLocks['risk_scenarios']}
	bind:cachedValue={formDataCache['risk_scenarios']}
	label={m.riskScenarios()}
	helpText={m.riskAcceptanceRiskScenariosHelpText()}
	disabled={initialData.risk_scenarios?.length > 0}
	multiple
/>
