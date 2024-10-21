<script lang="ts">
	import AutocompleteSelect from '../AutocompleteSelect.svelte';
	import Select from '../Select.svelte';
	import Checkbox from '$lib/components/Forms/Checkbox.svelte';
	import TextField from '$lib/components/Forms/TextField.svelte';
	import NumberField from '$lib/components/Forms/NumberField.svelte';
	import { getOptions } from '$lib/utils/crud';
	import type { SuperValidated } from 'sveltekit-superforms';
	import type { ModelInfo, CacheLock } from '$lib/utils/types';
	import * as m from '$paraglide/messages.js';

	export let form: SuperValidated<any>;
	export let model: ModelInfo;
	export let duplicate: boolean = false;
	export let cacheLocks: Record<string, CacheLock> = {};
	export let formDataCache: Record<string, any> = {};
	export let schema: any = {};
	export let initialData: Record<string, any> = {};
</script>

{#if !duplicate}
	{#if schema.shape.category}
		<Select
			{form}
			options={model.selectOptions['category']}
			field="category"
			label={m.category()}
			cacheLock={cacheLocks['category']}
			bind:cachedValue={formDataCache['category']}
		/>
	{/if}
	<Select
		{form}
		options={model.selectOptions['csf_function']}
		field="csf_function"
		label={m.csfFunction()}
		cacheLock={cacheLocks['csf_function']}
		bind:cachedValue={formDataCache['csf_function']}
	/>
	<AutocompleteSelect
		{form}
		multiple
		options={getOptions({ objects: model.foreignKeys['owner'], label: 'email' })}
		field="owner"
		cacheLock={cacheLocks['owner']}
		bind:cachedValue={formDataCache['owner']}
		label={m.owner()}
	/>
	<Select
		{form}
		options={model.selectOptions['status']}
		field="status"
		label={m.status()}
		cacheLock={cacheLocks['status']}
		bind:cachedValue={formDataCache['status']}
	/>
	<AutocompleteSelect
		{form}
		multiple
		options={getOptions({
			objects: model.foreignKeys['evidences'],
			extra_fields: [['folder', 'str']]
		})}
		field="evidences"
		cacheLock={cacheLocks['evidences']}
		bind:cachedValue={formDataCache['evidences']}
		label={m.evidences()}
	/>
	<TextField
		type="date"
		{form}
		field="start_date"
		label={m.startDate()}
		helpText={m.startDateHelpText()}
		cacheLock={cacheLocks['start_date']}
		bind:cachedValue={formDataCache['start_date']}
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
		type="date"
		{form}
		field="expiry_date"
		label={m.expiryDate()}
		helpText={m.expiryDateHelpText()}
		cacheLock={cacheLocks['expiry_date']}
		bind:cachedValue={formDataCache['expiry_date']}
	/>
	<TextField
		{form}
		field="link"
		label={m.link()}
		helpText={m.linkHelpText()}
		cacheLock={cacheLocks['link']}
		bind:cachedValue={formDataCache['link']}
	/>
	<Select
		{form}
		options={model.selectOptions['effort']}
		field="effort"
		label={m.effort()}
		helpText={m.effortHelpText()}
		cacheLock={cacheLocks['effort']}
		bind:cachedValue={formDataCache['effort']}
	/>
	<NumberField
		{form}
		field="cost"
		label={m.cost()}
		helpText={m.costHelpText()}
		cacheLock={cacheLocks['cost']}
		bind:cachedValue={formDataCache['cost']}
	/>
{/if}

{#if duplicate}
	<!-- We must set the right translation for this checkbox -->
	<!-- Duplicate the evidences -->
	<!-- If disabled, the applied control will be duplicated without its evidences -->
	<Checkbox
		{form}
		field="duplicate_evidences"
		label={m.showImagesUnauthenticated()}
		helpText={m.showImagesUnauthenticatedHelpText()}
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
