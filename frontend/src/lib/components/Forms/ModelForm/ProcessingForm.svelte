<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Select from '../Select.svelte';
	import Checkbox from '../Checkbox.svelte';
	import { formFieldProxy, type SuperValidated } from 'sveltekit-superforms';
	import { PROCESSOR_ROLES } from '$lib/utils/constants';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

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

	const { value: roleValue } = formFieldProxy(form as any, 'role');
	// Preset once when created from the processor register (same as CampaignForm's kind);
	// an effect here loops, since writing the form re-derives `initialData`.
	if (initialData.role) roleValue.set(initialData.role);
	const isProcessor = $derived(PROCESSOR_ROLES.includes($roleValue as string));
	// Art. 30(1)(a) needs co-controllers, Art. 30(2)(a) the controllers served
	const controllersLabel = $derived(
		$roleValue === 'privacy_joint_controller'
			? m.processingCoControllers()
			: $roleValue === 'privacy_sub_processor'
				? m.processingSubProcessorClients()
				: m.processingControllers()
	);
</script>

<AutocompleteSelect
	{form}
	field="status"
	options={model.selectOptions['status']}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
	label={m.status()}
/>
<AutocompleteSelect
	{form}
	field="role"
	options={model.selectOptions['role']}
	cacheLock={cacheLocks['role']}
	bind:cachedValue={formDataCache['role']}
	label={m.processingRole()}
	helpText={m.processingRoleHelpText()}
/>
{#if isProcessor || $roleValue === 'privacy_joint_controller'}
	<AutocompleteSelect
		{form}
		multiple
		optionsEndpoint="entities"
		optionsExtraFields={[['folder', 'str']]}
		field="controllers"
		cacheLock={cacheLocks['controllers']}
		bind:cachedValue={formDataCache['controllers']}
		label={controllersLabel}
		helpText={m.processingControllersHelpText()}
	/>
{/if}
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="actors?user__is_third_party=False"
	optionsLabelField="str"
	optionsInfoFields={{
		fields: [{ field: 'type', translate: true }],
		position: 'prefix'
	}}
	field="assigned_to"
	cacheLock={cacheLocks['assigned_to']}
	bind:cachedValue={formDataCache['assigned_to']}
	label={m.assignedTo()}
/>
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="terminologies?field_path=processing.nature&is_visible=true"
	optionsLabelField="translated_name"
	field="nature"
	label={m.processingNature()}
/>
<AutocompleteSelect
	multiple
	{form}
	createFromSelection={true}
	optionsEndpoint="filtering-labels"
	optionsLabelField="label"
	translateOptions={false}
	field="filtering_labels"
	helpText={m.labelsHelpText()}
	label={m.labels()}
	allowUserOptions="append"
/>

{#if !isProcessor}
	<Checkbox
		{form}
		field="dpia_required"
		label={m.dpiaRequired()}
		cacheLock={cacheLocks['dpia_required']}
		bind:cachedValue={formDataCache['dpia_required']}
	/>
	<TextField
		{form}
		field="dpia_reference"
		label={m.dpiaReference()}
		helpText={m.dpiaReferenceHelpText()}
		cacheLock={cacheLocks['dpia_reference']}
		bind:cachedValue={formDataCache['dpia_reference']}
	/>
{/if}
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="applied-controls"
	optionsExtraFields={[['folder', 'str']]}
	optionsInfoFields={{
		fields: [{ field: 'category', translate: true }],
		position: 'prefix'
	}}
	field="associated_controls"
	cacheLock={cacheLocks['associated_controls']}
	bind:cachedValue={formDataCache['associated_controls']}
	label={m.associatedAppliedControls()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="evidences"
	optionsExtraFields={[['folder', 'str']]}
	field="evidences"
	cacheLock={cacheLocks['evidences']}
	bind:cachedValue={formDataCache['evidences']}
	label={m.evidences()}
/>
<AutocompleteSelect
	{form}
	multiple
	optionsEndpoint="perimeters"
	optionsExtraFields={[['folder', 'str']]}
	field="perimeters"
	cacheLock={cacheLocks['perimeters']}
	bind:cachedValue={formDataCache['perimeters']}
	label={m.perimeters()}
/>
<!-- author = models.ForeignKey( -->
<!--     User, on_delete=models.SET_NULL, null=True, related_name="authored_processings" -->
<!-- ) -->
<!-- information_channel = models.CharField(max_length=255, blank=True) -->
<!-- usage_channel = models.CharField(max_length=255, blank=True) -->
<!-- dpia_required = models.BooleanField(default=False, blank=True) -->
<!-- dpia_reference = models.CharField(max_length=255, blank=True) -->
<!-- has_sensitive_personal_data = models.BooleanField(default=False) -->
<!-- owner = models.ForeignKey( -->
<!--     Entity, on_delete=models.SET_NULL, null=True, related_name="owned_processings" -->
<!-- ) -->
<!-- associated_controls = models.ManyToManyField( -->
<!--     AppliedControl, blank=True, related_name="processings" -->
<!-- ) -->
