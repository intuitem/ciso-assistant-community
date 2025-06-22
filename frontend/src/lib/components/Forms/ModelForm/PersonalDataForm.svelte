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

	console.log(model);
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
	field="category"
	options={model.selectOptions['category']}
	cacheLock={cacheLocks['category']}
	bind:cachedValue={formDataCache['category']}
	label={m.category()}
/>

<TextField
	{form}
	field="retention"
	label={m.retention()}
	cacheLock={cacheLocks['retention']}
	bind:cachedValue={formDataCache['retention']}
/>
<AutocompleteSelect
	{form}
	field="deletion_policy"
	options={model.selectOptions['deletion_policy']}
	cacheLock={cacheLocks['deletion_policy']}
	bind:cachedValue={formDataCache['deletion_policy']}
	label={m.deletionPolicy()}
/>
<AutocompleteSelect
	{form}
	field="processing"
	optionsEndpoint="processings"
	cacheLock={cacheLocks['processing']}
	bind:cachedValue={formDataCache['processing']}
	label={m.processing()}
	hidden={initialData.processing}
/>

<Checkbox
	{form}
	field="is_sensitive"
	label={m.isSensitive()}
	cacheLock={cacheLocks['is_sensitive']}
	bind:cachedValue={formDataCache['is_sensitive']}
/>
<!-- retention = models.CharField(max_length=255, blank=True) -->
<!-- deletion_policy = models.CharField( -->
<!--     max_length=50, choices=DELETION_POLICY_CHOICES, blank=True -->
<!-- ) -->
<!-- is_sensitive = models.BooleanField(default=False) -->
