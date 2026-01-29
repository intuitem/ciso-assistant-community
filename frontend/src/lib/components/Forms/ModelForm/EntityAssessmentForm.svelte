<script lang="ts">
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Score from '../Score.svelte';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';

	interface Props {
		form: SuperValidated<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		data?: Record<string, any>;
	}

	let {
		form,
		model = $bindable(),
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		data = {}
	}: Props = $props();

	let selectedFolder = $state<string | undefined>(undefined);
	let folderKey = $state(0);
	let isAutoFillingFolder = $state(false);

	function handleFolderChange(folderId: string) {
		selectedFolder = folderId;
		// Clear perimeter when folder changes (unless we're auto-filling from perimeter)
		if (!isAutoFillingFolder && form.data?.perimeter) {
			form.form.update((currentData) => ({
				...currentData,
				perimeter: undefined
			}));
		}
		isAutoFillingFolder = false;
	}

	async function handlePerimeterChange(perimeterId: string) {
		if (perimeterId && !selectedFolder) {
			// Fetch perimeter to get its folder and auto-fill
			try {
				const response = await fetch(`/perimeters/${perimeterId}`);
				if (response.ok) {
					const perimeter = await response.json();
					if (perimeter.folder?.id) {
						isAutoFillingFolder = true;
						selectedFolder = perimeter.folder.id;
						// Update form data and force folder component to re-render
						form.form.update((currentData) => ({
							...currentData,
							folder: perimeter.folder.id
						}));
						folderKey++;
					}
				}
			} catch (error) {
				console.error('Error fetching perimeter:', error);
			}
		}
	}
</script>

{#key folderKey}
	<AutocompleteSelect
		{form}
		optionsEndpoint="folders"
		field="folder"
		cacheLock={cacheLocks['folder']}
		bind:cachedValue={formDataCache['folder']}
		label={m.folder()}
		onChange={handleFolderChange}
		mount={handleFolderChange}
	/>
{/key}
{#key selectedFolder}
	<AutocompleteSelect
		{form}
		optionsEndpoint="perimeters"
		optionsDetailedUrlParameters={selectedFolder ? [['folder', selectedFolder]] : []}
		optionsExtraFields={[['folder', 'str']]}
		field="perimeter"
		nullable
		cacheLock={cacheLocks['perimeter']}
		bind:cachedValue={formDataCache['perimeter']}
		label={m.perimeter()}
		onChange={handlePerimeterChange}
	/>
{/key}
{#if !data.compliance_assessment}
	<Checkbox
		{form}
		field="create_audit"
		label={m.createAudit()}
		helpText={m.createAuditHelpText()}
	/>
	<AutocompleteSelect
		{form}
		disabled={!data.create_audit}
		mandatory
		hidden={!data.create_audit}
		optionsEndpoint="frameworks"
		field="framework"
		cacheLock={cacheLocks['framework']}
		bind:cachedValue={formDataCache['framework']}
		label={m.framework()}
		onChange={async (e) => {
			if (e) {
				await fetch(`/frameworks/${e}`)
					.then((r) => r.json())
					.then((r) => {
						const implementation_groups = r['implementation_groups_definition'] || [];
						model.selectOptions['selected_implementation_groups'] = implementation_groups.map(
							(group) => ({ label: group.name, value: group.ref_id })
						);
					});
			}
		}}
	/>
	{#if model.selectOptions['selected_implementation_groups'] && model.selectOptions['selected_implementation_groups'].length}
		<AutocompleteSelect
			multiple
			translateOptions={false}
			{form}
			options={model.selectOptions['selected_implementation_groups']}
			field="selected_implementation_groups"
			cacheLock={cacheLocks['selected_implementation_groups']}
			bind:cachedValue={formDataCache['selected_implementation_groups']}
			label={m.selectedImplementationGroups()}
		/>
	{/if}
{/if}
<AutocompleteSelect
	{form}
	optionsEndpoint="entities"
	field="entity"
	cacheLock={cacheLocks['entity']}
	bind:cachedValue={formDataCache['entity']}
	label={m.entity()}
	hidden={initialData.entity}
/>
{#key form.data?.entity}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="solutions"
		optionsDetailedUrlParameters={[['provider_entity', form.data?.entity || '']]}
		field="solutions"
		cacheLock={cacheLocks['solutions']}
		bind:cachedValue={formDataCache['solutions']}
		label={m.solutions()}
	/>
{/key}
<Score
	{form}
	label={m.criticality()}
	field="criticality"
	inversedColors
	fullDonut
	min_score={1}
	max_score={4}
/>
<TextField
	type="date"
	{form}
	field="due_date"
	label={m.dueDate()}
	helpText={m.dueDateHelpText()}
	cacheLock={cacheLocks['due_date']}
	bind:cachedValue={formDataCache['due_date']}
/>
{#if form.data?.entity}
	{#key form.data?.entity}
		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="users"
			optionsDetailedUrlParameters={[
				['is_third_party', 'true'],
				['representative__entity', form.data?.entity || '']
			]}
			optionsLabelField="email"
			field="representatives"
			helpText={m.entityAssessmentRepresentativesHelpText()}
			cacheLock={cacheLocks['representatives']}
			bind:cachedValue={formDataCache['representatives']}
			label={m.representatives()}
		/>
	{/key}
{/if}
<Select
	{form}
	options={model.selectOptions['conclusion']}
	field="conclusion"
	label={m.conclusion()}
	cacheLock={cacheLocks['conclusion']}
	bind:cachedValue={formDataCache['conclusion']}
/>
<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<Select
		{form}
		options={model.selectOptions['status']}
		field="status"
		label={m.status()}
		cacheLock={cacheLocks['status']}
		bind:cachedValue={formDataCache['status']}
	/>
	<TextField
		type="date"
		{form}
		field="eta"
		label={m.eta()}
		helpText={m.etaHelpText()}
		cacheLock={cacheLocks['eta']}
		bind:cachedValue={formDataCache['eta']}
	/>
	<TextField
		{form}
		field="version"
		label={m.version()}
		cacheLock={cacheLocks['version']}
		bind:cachedValue={formDataCache['version']}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="actors"
		optionsLabelField="str"
		optionsInfoFields={{
			fields: [{ field: 'type', translate: true }],
			position: 'prefix'
		}}
		field="authors"
		cacheLock={cacheLocks['authors']}
		bind:cachedValue={formDataCache['authors']}
		label={m.authors()}
	/>
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="actors"
		optionsLabelField="str"
		optionsInfoFields={{
			fields: [{ field: 'type', translate: true }],
			position: 'prefix'
		}}
		field="reviewers"
		cacheLock={cacheLocks['reviewers']}
		bind:cachedValue={formDataCache['reviewers']}
		label={m.reviewers()}
	/>
	<AutocompleteSelect
		{form}
		optionsEndpoint="compliance-assessments"
		optionsExtraFields={[['folder', 'str']]}
		field="compliance_assessment"
		cacheLock={cacheLocks['compliance_assessment']}
		bind:cachedValue={formDataCache['compliance_assessment']}
		label={m.complianceAssessment()}
		disabled={data.create_audit}
		hidden={data.create_audit}
	/>
	<AutocompleteSelect
		{form}
		optionsEndpoint="evidences"
		optionsExtraFields={[['folder', 'str']]}
		field="evidence"
		cacheLock={cacheLocks['evidence']}
		bind:cachedValue={formDataCache['evidence']}
		label={m.evidence()}
		helpText={m.entityAssessmentEvidenceHelpText()}
	/>
	<TextArea
		{form}
		field="observation"
		label={m.observation()}
		cacheLock={cacheLocks['observation']}
		bind:cachedValue={formDataCache['observation']}
	/>
	<TextField
		{form}
		field="reference_link"
		label={m.referenceLink()}
		helpText={m.linkHelpText()}
		cacheLock={cacheLocks['reference_link']}
		bind:cachedValue={formDataCache['reference_link']}
	/>
</Dropdown>
