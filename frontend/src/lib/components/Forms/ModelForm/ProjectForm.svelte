<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import FolderTreeSelect from '../FolderTreeSelect.svelte';
	import TextField from '../TextField.svelte';
	import TextArea from '../TextArea.svelte';
	import Select from '../Select.svelte';
	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import type { CacheLock, ModelInfo } from '$lib/utils/types';
	import type { SuperValidated } from 'sveltekit-superforms';
	import { m } from '$paraglide/messages';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: any;
	}

	let {
		form,
		model,
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {}
	}: Props = $props();
</script>

<TextField
	{form}
	field="ref_id"
	cacheLock={cacheLocks['ref_id']}
	bind:cachedValue={formDataCache['ref_id']}
	label={m.refId()}
/>

<FolderTreeSelect
	{form}
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
/>

<AutocompleteSelect
	{form}
	optionsEndpoint="actors?user__is_third_party=False"
	optionsLabelField="str"
	field="owner"
	cacheLock={cacheLocks['owner']}
	bind:cachedValue={formDataCache['owner']}
	nullable={true}
	label={m.owner()}
	helpText={m.projectOwnerHelpText()}
/>

<AutocompleteSelect
	{form}
	optionsEndpoint="actors?user__is_third_party=False"
	optionsLabelField="str"
	field="sponsor"
	cacheLock={cacheLocks['sponsor']}
	bind:cachedValue={formDataCache['sponsor']}
	nullable={true}
	label={m.sponsor()}
	helpText={m.projectSponsorHelpText()}
/>

<AutocompleteSelect
	{form}
	optionsEndpoint="terminologies?field_path=project.status&is_visible=true"
	optionsLabelField="translated_name"
	field="status"
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
	nullable={true}
	label={m.projectStatus()}
/>

<Select
	{form}
	options={model.selectOptions?.['priority'] ?? []}
	field="priority"
	label={m.projectPriority()}
	cacheLock={cacheLocks['priority']}
	bind:cachedValue={formDataCache['priority']}
/>

<AutocompleteSelect
	{form}
	optionsEndpoint="terminologies?field_path=project.health&is_visible=true"
	optionsLabelField="translated_name"
	field="health"
	cacheLock={cacheLocks['health']}
	bind:cachedValue={formDataCache['health']}
	nullable={true}
	label={m.projectHealth()}
/>

<TextField
	type="date"
	{form}
	field="start_date"
	cacheLock={cacheLocks['start_date']}
	bind:cachedValue={formDataCache['start_date']}
	label={m.startDate()}
/>

<TextField
	type="date"
	{form}
	field="end_date"
	cacheLock={cacheLocks['end_date']}
	bind:cachedValue={formDataCache['end_date']}
	label={m.endDate()}
/>

<TextField
	type="date"
	{form}
	field="eta"
	cacheLock={cacheLocks['eta']}
	bind:cachedValue={formDataCache['eta']}
	label={m.eta()}
/>

<TextField
	type="number"
	{form}
	field="progress"
	cacheLock={cacheLocks['progress']}
	bind:cachedValue={formDataCache['progress']}
	label={m.progress()}
/>

<AutocompleteSelect
	{form}
	optionsEndpoint="generic-collections"
	optionsLabelField="auto"
	optionsExtraFields={[['folder', 'str']]}
	field="linked_collection"
	cacheLock={cacheLocks['linked_collection']}
	bind:cachedValue={formDataCache['linked_collection']}
	nullable={true}
	label={m.linkedCollection()}
/>

<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<TextField
		{form}
		field="ref_link"
		cacheLock={cacheLocks['ref_link']}
		bind:cachedValue={formDataCache['ref_link']}
		label={m.refLink()}
		helpText={m.refLinkHelpText()}
	/>
	<AutocompleteSelect
		{form}
		optionsEndpoint="projects"
		optionsLabelField="auto"
		optionsExtraFields={[['folder', 'str']]}
		field="parent_project"
		cacheLock={cacheLocks['parent_project']}
		bind:cachedValue={formDataCache['parent_project']}
		nullable={true}
		label={m.parentProject()}
	/>
	<TextArea
		{form}
		field="purpose"
		label={m.purpose()}
		cacheLock={cacheLocks['purpose']}
		bind:cachedValue={formDataCache['purpose']}
	/>
	<TextArea
		{form}
		field="objectives"
		label={m.objectives()}
		cacheLock={cacheLocks['objectives']}
		bind:cachedValue={formDataCache['objectives']}
	/>
	<TextArea
		{form}
		field="success_criteria"
		label={m.successCriteria()}
		cacheLock={cacheLocks['success_criteria']}
		bind:cachedValue={formDataCache['success_criteria']}
	/>
	<TextArea
		{form}
		field="business_case"
		label={m.businessCase()}
		cacheLock={cacheLocks['business_case']}
		bind:cachedValue={formDataCache['business_case']}
	/>
	<TextArea
		{form}
		field="deliverables"
		label={m.deliverables()}
		cacheLock={cacheLocks['deliverables']}
		bind:cachedValue={formDataCache['deliverables']}
	/>
	<TextArea
		{form}
		field="assumptions"
		label={m.assumptions()}
		cacheLock={cacheLocks['assumptions']}
		bind:cachedValue={formDataCache['assumptions']}
	/>
	<TextArea
		{form}
		field="constraints"
		label={m.constraints()}
		cacheLock={cacheLocks['constraints']}
		bind:cachedValue={formDataCache['constraints']}
	/>
	<TextArea
		{form}
		field="dependencies_note"
		label={m.dependenciesNote()}
		cacheLock={cacheLocks['dependencies_note']}
		bind:cachedValue={formDataCache['dependencies_note']}
	/>
	<TextArea
		{form}
		field="exit_criteria"
		label={m.exitCriteria()}
		cacheLock={cacheLocks['exit_criteria']}
		bind:cachedValue={formDataCache['exit_criteria']}
	/>
	<TextArea
		{form}
		field="organizational_alignment"
		label={m.organizationalAlignment()}
		cacheLock={cacheLocks['organizational_alignment']}
		bind:cachedValue={formDataCache['organizational_alignment']}
	/>
	<TextArea
		{form}
		field="approval_requirements"
		label={m.approvalRequirements()}
		cacheLock={cacheLocks['approval_requirements']}
		bind:cachedValue={formDataCache['approval_requirements']}
	/>
	<TextField
		type="number"
		{form}
		field="budget"
		cacheLock={cacheLocks['budget']}
		bind:cachedValue={formDataCache['budget']}
		label={m.budget()}
	/>
	<TextField
		{form}
		field="currency"
		cacheLock={cacheLocks['currency']}
		bind:cachedValue={formDataCache['currency']}
		label={m.currency()}
	/>
	<AutocompleteSelect
		multiple
		{form}
		createFromSelection={true}
		optionsEndpoint="filtering-labels"
		optionsLabelField="label"
		field="filtering_labels"
		helpText={m.labelsHelpText()}
		label={m.labels()}
		translateOptions={false}
		allowUserOptions="append"
	/>
	<TextArea
		{form}
		field="observation"
		label={m.observation()}
		helpText={m.observationHelpText()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
</Dropdown>
