<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { superForm } from 'sveltekit-superforms';
	import { zod } from 'sveltekit-superforms/adapters';
	import * as m from '$paraglide/messages.js';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import Select from '$lib/components/Forms/Select.svelte';
	import AutocompleteSelect from '$lib/components/Forms/AutocompleteSelect.svelte';
	import { Accordion } from '@skeletonlabs/skeleton-svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';

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

	let openAccordionItems = $state([]);
</script>

<TextField
	{form}
	field="ref_id"
	label={m.refId()}
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
/>

<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="users?is_third_party=false"
	optionsLabelField="email"
	field="assigned_to"
	cacheLock={cacheLocks['assigned_to']}
	bind:cachedValue={formDataCache['assigned_to']}
	label={m.assignedTo()}
/>

<TextField
	{form}
	field="discovered_on"
	type="datetime-local"
	label={m.discoveredOn()}
	cacheLock={cacheLocks['discovered_on']}
	bind:cachedValue={formDataCache['discovered_on']}
/>

<AutocompleteSelect
	{form}
	field="breach_type"
	options={model.selectOptions['breach_type']}
	cacheLock={cacheLocks['breach_type']}
	bind:cachedValue={formDataCache['breach_type']}
	label={m.breachType()}
/>

<AutocompleteSelect
	{form}
	field="risk_level"
	options={model.selectOptions['risk_level']}
	cacheLock={cacheLocks['risk_level']}
	bind:cachedValue={formDataCache['risk_level']}
	label={m.dataBreachRiskLevel()}
	helpText={m.dataBreachRiskLevelHelpText()}
/>

<AutocompleteSelect
	{form}
	field="status"
	options={model.selectOptions['status']}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
	label={m.status()}
/>

<Accordion
	value={openAccordionItems}
	onValueChange={(e) => (openAccordionItems = e.value)}
	multiple
>
	<Accordion.Item value="assessment">
		{#snippet control()}
			<i class="fa-solid fa-chart-line mr-2"></i>{m.riskAssessment()}
		{/snippet}
		{#snippet panel()}
			<div class="flex flex-col space-y-3 p-4">
				<TextField
					{form}
					field="affected_subjects_count"
					type="number"
					label={m.affectedSubjectsCount()}
					cacheLock={cacheLocks['affected_subjects_count']}
					bind:cachedValue={formDataCache['affected_subjects_count']}
				/>

				<AutocompleteSelect
					{form}
					field="affected_processings"
					multiple
					optionsEndpoint="processings"
					optionsExtraFields={[['folder', 'str']]}
					cacheLock={cacheLocks['affected_processings']}
					bind:cachedValue={formDataCache['affected_processings']}
					label={m.affectedProcessings()}
				/>

				<AutocompleteSelect
					{form}
					field="affected_personal_data"
					multiple
					optionsEndpoint="personal-data"
					optionsExtraFields={[['folder', 'str']]}
					cacheLock={cacheLocks['affected_personal_data']}
					bind:cachedValue={formDataCache['affected_personal_data']}
					label={m.affectedPersonalData()}
				/>

				<TextField
					{form}
					field="affected_personal_data_count"
					type="number"
					label={m.affectedPersonalDataCount()}
					cacheLock={cacheLocks['affected_personal_data_count']}
					bind:cachedValue={formDataCache['affected_personal_data_count']}
				/>

				<MarkdownField
					{form}
					field="potential_consequences"
					label={m.potentialConsequences()}
					cacheLock={cacheLocks['potential_consequences']}
					bind:cachedValue={formDataCache['potential_consequences']}
				/>
			</div>
		{/snippet}
	</Accordion.Item>

	<Accordion.Item value="authority">
		{#snippet control()}
			<i class="fa-solid fa-landmark mr-2"></i>{m.authorities()}
		{/snippet}
		{#snippet panel()}
			<div class="flex flex-col space-y-3 p-4">
				<AutocompleteSelect
					{form}
					field="authorities"
					multiple
					optionsEndpoint="entities?relationship__name=regulatory_authority"
					cacheLock={cacheLocks['authorities']}
					bind:cachedValue={formDataCache['authorities']}
					label={m.authorities()}
				/>

				<TextField
					{form}
					field="authority_notified_on"
					type="datetime-local"
					label={m.authorityNotifiedOn()}
					cacheLock={cacheLocks['authority_notified_on']}
					bind:cachedValue={formDataCache['authority_notified_on']}
				/>

				<TextField
					{form}
					field="authority_notification_ref"
					label={m.authorityNotificationRef()}
					cacheLock={cacheLocks['authority_notification_ref']}
					bind:cachedValue={formDataCache['authority_notification_ref']}
				/>
			</div>
		{/snippet}
	</Accordion.Item>

	<Accordion.Item value="treatment">
		{#snippet control()}
			<i class="fa-solid fa-shield-halved mr-2"></i>{m.treatment()}
		{/snippet}
		{#snippet panel()}
			<div class="flex flex-col space-y-3 p-4">
				<AutocompleteSelect
					{form}
					field="incident"
					optionsEndpoint="incidents"
					optionsExtraFields={[['folder', 'str']]}
					cacheLock={cacheLocks['incident']}
					bind:cachedValue={formDataCache['incident']}
					label={m.incident()}
				/>

				<TextField
					{form}
					field="subjects_notified_on"
					type="datetime-local"
					label={m.subjectsNotifiedOn()}
					cacheLock={cacheLocks['subjects_notified_on']}
					bind:cachedValue={formDataCache['subjects_notified_on']}
				/>

				<AutocompleteSelect
					{form}
					field="remediation_measures"
					multiple
					optionsEndpoint="applied-controls"
					optionsExtraFields={[['folder', 'str']]}
					cacheLock={cacheLocks['remediation_measures']}
					bind:cachedValue={formDataCache['remediation_measures']}
					label={m.remediationMeasures()}
				/>

				<TextField
					{form}
					field="reference_link"
					type="url"
					label={m.referenceLink()}
					cacheLock={cacheLocks['reference_link']}
					bind:cachedValue={formDataCache['reference_link']}
				/>

				<MarkdownField
					{form}
					field="observation"
					label={m.observation()}
					cacheLock={cacheLocks['observation']}
					bind:cachedValue={formDataCache['observation']}
				/>
			</div>
		{/snippet}
	</Accordion.Item>
</Accordion>

<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
	pathField="path"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
/>
