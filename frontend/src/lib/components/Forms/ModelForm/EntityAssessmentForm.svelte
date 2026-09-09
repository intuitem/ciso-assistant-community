<script lang="ts">
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import FolderTreeSelect from '$lib/components/Forms/FolderTreeSelect.svelte';
	import Select from '../Select.svelte';
	import MarkdownField from '$lib/components/Forms/MarkdownField.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import Score from '../Score.svelte';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import { m } from '$paraglide/messages';

	import Dropdown from '$lib/components/Dropdown/Dropdown.svelte';
	import VisibilityEditor from '$lib/components/ComplianceAssessment/VisibilityEditor.svelte';
	import type { SuperForm } from 'sveltekit-superforms';

	interface Props {
		form: SuperForm<any>;
		model: ModelInfo;
		cacheLocks?: Record<string, CacheLock>;
		formDataCache?: Record<string, any>;
		initialData?: Record<string, any>;
		object?: Record<string, any>;
		context?: string;
	}

	let {
		form,
		model = $bindable(),
		cacheLocks = {},
		formDataCache = $bindable({}),
		initialData = {},
		object = {},
		context = 'default'
	}: Props = $props();

	const { form: formData } = form;

	// Creating almost always means sending a questionnaire, so the audit is on by
	// default; on edit it stays off. `??` would keep the schema's `false`.
	let createAudit = $state(context === 'create' ? true : ($formData.create_audit ?? false));
	let selectedEntity = $state<string | undefined>(form.data?.entity || initialData.entity);

	// The assessment belongs where the third party does. Preselected so the two cannot
	// silently diverge, but still editable for the odd cross-domain review.
	async function handleEntityChange(entityId: string | undefined) {
		selectedEntity = entityId;
		if (!entityId || initialData.folder) return;
		const folderWhenAsked = $formData.folder;
		try {
			const entity = await fetch(`/entities/${entityId}`).then((res) => res.json());
			// Neither a slower earlier response nor a folder the user picked meanwhile
			// may be overwritten by this one.
			if (entityId !== selectedEntity || $formData.folder !== folderWhenAsked) return;
			const folderId = entity?.folder?.id ?? entity?.folder;
			if (folderId) form.form.update((data) => ({ ...data, folder: folderId }), { taint: false });
		} catch (e) {
			console.error('Could not resolve the entity folder', e);
		}
	}
	let implementationGroupsChoices = $state<{ label: string; value: string }[]>([]);
	let frameworkDefaults = $state<Record<string, any> | null>(null);

	let auditDefaultApplied = false;
	$effect(() => {
		if (auditDefaultApplied || context !== 'create') return;
		auditDefaultApplied = true;
		form.form.update((d) => ({ ...d, create_audit: createAudit }));
	});

	let auditData = $derived(
		object.compliance_assessment && typeof object.compliance_assessment === 'object'
			? object.compliance_assessment
			: object.compliance_assessment
				? { id: object.compliance_assessment, str: '', name: '' }
				: null
	);
</script>

<AutocompleteSelect
	{form}
	optionsEndpoint="entities"
	optionsExtraFields={[['folder', 'str']]}
	field="entity"
	cacheLock={cacheLocks['entity']}
	bind:cachedValue={formDataCache['entity']}
	label={m.entity()}
	hidden={initialData.entity}
	onChange={handleEntityChange}
/>
<FolderTreeSelect
	{form}
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
/>

{#if auditData}
	<AutocompleteSelect
		{form}
		optionsEndpoint="compliance-assessments"
		optionsExtraFields={[['folder', 'str']]}
		field="compliance_assessment"
		cacheLock={cacheLocks['compliance_assessment']}
		bind:cachedValue={formDataCache['compliance_assessment']}
		label={m.complianceAssessment()}
		disabled
	/>
	<a href="/compliance-assessments/{auditData.id}" class="anchor flex items-center space-x-2">
		<span>{m.jumpTo()}</span>
		<i class="fa-solid fa-link text-xs"></i>
	</a>
{:else}
	<Checkbox
		{form}
		field="create_audit"
		label={m.createAudit()}
		helpText={m.createAuditHelpText()}
		onChange={(checked) => (createAudit = checked)}
	/>
	<AutocompleteSelect
		{form}
		disabled={!createAudit}
		mandatory
		hidden={!createAudit}
		optionsEndpoint="frameworks"
		field="framework"
		cacheLock={cacheLocks['framework']}
		bind:cachedValue={formDataCache['framework']}
		label={m.framework()}
		onChange={async (e) => {
			if (!e) {
				// Clearing the framework takes the baseline with it, so the editor hides
				// again rather than keeping the previous framework's pills on screen.
				frameworkDefaults = null;
				implementationGroupsChoices = [];
				form.form.update((d) => ({
					...d,
					field_visibility: {},
					selected_implementation_groups: []
				}));
				return;
			}
			if (e) {
				await fetch(`/frameworks/${e}`)
					.then((r) => r.json())
					.then((r) => {
						// A slower earlier response must not apply another framework's defaults.
						if (e !== $formData.framework) return;
						const implementation_groups = r['implementation_groups_definition'] || [];
						implementationGroupsChoices = implementation_groups.map((group) => ({
							label: group.name,
							value: group.ref_id
						}));
						// This form only ever creates audits addressed to a third party, so the
						// pills must show that profile — not the internal-audit defaults.
						frameworkDefaults =
							r['third_party_field_visibility'] ?? r['effective_field_visibility'] ?? null;
						// Groups belong to the framework that defined them.
						form.form.update((d) => ({
							...d,
							field_visibility: {},
							selected_implementation_groups: []
						}));
					});
			}
		}}
	/>
	{#if implementationGroupsChoices.length > 0}
		{#key implementationGroupsChoices}
			<AutocompleteSelect
				multiple
				translateOptions={false}
				{form}
				options={implementationGroupsChoices}
				field="selected_implementation_groups"
				cacheLock={cacheLocks['selected_implementation_groups']}
				bind:cachedValue={formDataCache['selected_implementation_groups']}
				label={m.selectedImplementationGroups()}
			/>
		{/key}
	{/if}
	<!-- Only once the framework is known: until then the editor has no baseline to
	     show and falls back to "everyone" for every field, which is neither the
	     profile nor what would be saved. -->
	{#if createAudit && frameworkDefaults}
		<VisibilityEditor
			value={$formData.field_visibility}
			onChange={(next) => form.form.update((d) => ({ ...d, field_visibility: next }))}
			{frameworkDefaults}
		/>
	{/if}
{/if}
{#key selectedEntity}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="solutions"
		optionsDetailedUrlParameters={[['provider_entity', selectedEntity || '']]}
		optionsExtraFields={[['provider_entity', 'str']]}
		field="solutions"
		cacheLock={cacheLocks['solutions']}
		bind:cachedValue={formDataCache['solutions']}
		label={m.solutions()}
	/>
{/key}
{#if selectedEntity}
	{#key selectedEntity}
		<AutocompleteSelect
			{form}
			multiple
			optionsEndpoint="users"
			optionsDetailedUrlParameters={[
				['is_third_party', 'true'],
				['representative__entity', selectedEntity || '']
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
<TextField
	type="date"
	{form}
	field="due_date"
	label={m.dueDate()}
	helpText={m.dueDateHelpText()}
	cacheLock={cacheLocks['due_date']}
	bind:cachedValue={formDataCache['due_date']}
/>
<Dropdown open={false} style="hover:text-primary-700" icon="fa-solid fa-list" header={m.more()}>
	<Score
		{form}
		label={m.criticality()}
		field="criticality"
		inversedColors
		fullDonut
		min_score={1}
		max_score={4}
	/>
	<Select
		{form}
		options={model.selectOptions['conclusion']}
		field="conclusion"
		label={m.conclusion()}
		cacheLock={cacheLocks['conclusion']}
		bind:cachedValue={formDataCache['conclusion']}
	/>
	<TextField
		type="date"
		{form}
		field="expiry_date"
		label={m.expiryDate()}
		helpText={m.entityAssessmentExpiryDateHelpText()}
		cacheLock={cacheLocks['expiry_date']}
		bind:cachedValue={formDataCache['expiry_date']}
	/>
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
		optionsEndpoint="evidences"
		optionsExtraFields={[['folder', 'str']]}
		field="evidence"
		cacheLock={cacheLocks['evidence']}
		bind:cachedValue={formDataCache['evidence']}
		label={m.evidence()}
		helpText={m.entityAssessmentEvidenceHelpText()}
	/>
	<MarkdownField
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
