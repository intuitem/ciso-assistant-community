<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import TextArea from '$lib/components/Forms/TextArea.svelte';
	import Select from '../Select.svelte';
	import Checkbox from '../Checkbox.svelte';
	import type { SuperValidated } from 'sveltekit-superforms';
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
	field="status"
	options={model.selectOptions['status']}
	cacheLock={cacheLocks['status']}
	bind:cachedValue={formDataCache['status']}
	label={m.status()}
/>
<AutocompleteSelect
	multiple
	{form}
	optionsEndpoint="processing-natures"
	field="nature"
	label={m.processingNature()}
/>
<AutocompleteSelect
	{form}
	field="legal_basis"
	options={model.selectOptions['legal_basis']}
	cacheLock={cacheLocks['legal_basis']}
	bind:cachedValue={formDataCache['legal_basis']}
	translateOptions={true}
	label={m.legalBasis()}
/>
<AutocompleteSelect
	{form}
	optionsEndpoint="folders?content_type=DO&content_type=GL"
	field="folder"
	cacheLock={cacheLocks['folder']}
	bind:cachedValue={formDataCache['folder']}
	label={m.domain()}
	hidden={initialData.folder}
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
	allowUserOptions="append"
/>

<Checkbox
	{form}
	field="dpia_required"
	label={m.dpiaRequired()}
	cacheLock={cacheLocks['dpia_required']}
	bind:cachedValue={formDataCache['dpia_required']}
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
